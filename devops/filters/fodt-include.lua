
-- Function to read file content
local function read_file(path)
  local file = io.open(path, "r")
  if not file then
    return nil
  end
  local content = file:read("*a")
  file:close()
  return content
end

-- Function to extract text content from ODT office:text section
local function extract_body_content(content_xml)
  if not content_xml then
    return nil
  end
  
  -- Extract content between <office:text> and </office:text>
  local text_start = content_xml:find("<office:text>")
  local text_end = content_xml:find("</office:text>")
  
  if text_start and text_end then
    -- Get the content inside office:text, excluding sequence declarations
    local full_text = content_xml:sub(text_start + 14, text_end - 1) -- +14 for "<office:text>", -1 to exclude closing tag
    
    -- Skip sequence declarations and get actual content
    local content_start = full_text:find("</text:sequence%-decls>")
    if content_start then
      local actual_content = full_text:sub(content_start + 23) -- +23 for "</text:sequence-decls>"
      -- Trim whitespace
      actual_content = actual_content:match("^%s*(.-)%s*$")
      print("Extracted content length: " .. #actual_content)
      return actual_content
    else
      -- No sequence declarations, return all content
      local trimmed = full_text:match("^%s*(.-)%s*$")
      print("Extracted content length (no decls): " .. #trimmed)
      return trimmed
    end
  end
  
  return nil
end

-- Function to check if include file exists and determine type
local function check_include_file(include_path)
  local function exists(p)
    local f = io.open(p, "r")
    if f then f:close() return true end
    return false
  end

  -- Try the path as given
  if exists(include_path) then
    if include_path:match("%.fodt$") then
      return include_path, ".fodt"
    end
  end

  -- Try resolving relative to current working directory
  local cwd = os.getenv("PWD") or os.getenv("CD") or io.popen("cd"):read("*l")
  if cwd and cwd ~= "" then
    -- Join with '/' which works with pandoc and Lua on Windows too
    local sep = "/"
    -- If cwd already ends with a separator, avoid doubling
    if cwd:sub(-1) == '/' or cwd:sub(-1) == '\\' then
      sep = ''
    end
    local candidate = cwd .. sep .. include_path
    if exists(candidate) then
      if candidate:match("%.fodt$") then
        return candidate, ".fodt"
      end
    end
  end

  return nil, nil
end

-- Function to process include content
local function process_include(include_path, style, alt, return_type)
  return_type = return_type or "block"
  
  -- Check if the include file exists and get its type
  local include_file_path, file_extension = check_include_file(include_path)
  
  if include_file_path then
    print("Found include file: " .. include_file_path)
    
    if file_extension == ".fodt" then
      -- Handle FODT files (flat ODT) by reading directly
      local fodt_content = read_file(include_file_path)
      local body_content = extract_body_content(fodt_content)
      
      if body_content then
        print("Successfully loaded FODT content for include: " .. include_path)
        -- No wrap-mode support: return body content as-is
        if return_type == "inline" then
          return pandoc.RawInline("opendocument", body_content)
        else
          return pandoc.RawBlock("opendocument", body_content)
        end
      else
        print("Warning: Could not extract body content from FODT for include: " .. include_path)
      end
    end
  end

  -- Fallback to placeholder if file not found or content extraction failed
  print("Warning: Include file not found or not supported: " .. include_path)
  local xml = string.format('<text:p text:style-name="%s">«INCLUDE:%s:%s»</text:p>', style, include_path, alt)
  if return_type == "inline" then
    return pandoc.RawInline("opendocument", xml)
  else
    return pandoc.RawBlock("opendocument", xml)
  end
end

-- Handle DIV blocks with include class
function Div(el)
  -- Robustly detect class 'include' (el.classes may be a list table)
  local is_include = false
  if el.classes then
    for _, c in ipairs(el.classes) do
      if c == "include" then is_include = true break end
    end
  end

  if is_include then
    -- Accept several possible attribute names that authors might use
    -- Support pandoc attribute shorthand forms such as ::{.include src="..."}
    local function pick_src(attr)
      return el.attributes[attr]
    end

    local src = pick_src("src") or ""
    local style = el.attributes["style"] or "Default Paragraph Style"
    local alt = el.attributes["alt"]  or src

    if src ~= "" then
      return process_include(src, style, alt, "block")
    else
      -- No source provided; keep block unchanged but emit a placeholder for visibility
      local xml = string.format('<text:p text:style-name="%s">«INCLUDE:missing-src»</text:p>', style)
      return pandoc.RawBlock("opendocument", xml)
    end
  end
end

-- Function to get raw include content for inline embedding
local function get_include_content_raw(include_src)
  -- Check if the include file exists and get its type
  local include_file_path, file_extension = check_include_file(include_src)
  
  if include_file_path then
    print("Found include file: " .. include_file_path)
    
    if file_extension == ".fodt" then
      -- Handle FODT files directly
      local fodt_content = read_file(include_file_path)
      local body_content = extract_body_content(fodt_content)
      
      if body_content then
        print("Successfully loaded FODT content: " .. include_src)
        return body_content
      end
      
    end
  end
  
  return nil
end

-- Handle Image elements - replace include images with raw FODT content
function Image(img)
    -- Check if this is a include
  if img.src:match("^resources/includes/") and img.src:match("%.fodt$") then
        print("Processing include image: " .. img.src)
        
        -- Get raw include content
        local include_content = get_include_content_raw(img.src)
        if include_content then
            print("Successfully extracted include content: " .. img.src)
            -- Create a placeholder that will be processed later
            local placeholder = pandoc.Span({pandoc.Str("INCLUDE_PLACEHOLDER:" .. img.src)})
            placeholder.attributes = placeholder.attributes or {}
            placeholder.attributes["data-include-content"] = include_content
            return placeholder
        else
            print("Failed to process include: " .. img.src)
        end
    end
    
    return img
end

-- Document-level processing to replace include placeholders with actual content
function Pandoc(doc)
    print("Pandoc function called with " .. #doc.blocks .. " blocks")
    local blocks = {}
    
    for i, block in ipairs(doc.blocks) do
        if block.t == "Para" then
            -- Check if this paragraph contains a include placeholder
            local has_include_placeholder = false
            local include_content = nil
            
            for j, content in ipairs(block.content) do
                if content.t == "Span" and content.attributes and content.attributes["content"] then
                    has_include_placeholder = true
                    include_content = content.attributes["content"]
                    print("Found include placeholder in paragraph")
                    break
                end
            end
            
            if has_include_placeholder then
                print("Replacing include placeholder with ODT content")
                -- Insert raw ODT content as block
                table.insert(blocks, pandoc.RawBlock("opendocument", include_content))
            else
                table.insert(blocks, block)
            end
        else
            table.insert(blocks, block)
        end
    end
    
    print("Returning document with " .. #blocks .. " blocks")
    return pandoc.Pandoc(blocks, doc.meta)
end

-- Function to extract include paragraphs as Pandoc blocks
local function get_include_paragraphs(include_src)
  -- Check if the include file exists and get its type
  local include_file_path, file_extension = check_include_file(include_src)
  
  if include_file_path then
    print("Found include file for paragraphs: " .. include_file_path)
    
    if file_extension == ".fodt" then
      -- Handle FODT files directly
      local fodt_content = read_file(include_file_path)
      local body_content = extract_body_content(fodt_content)
      
      if body_content then
        print("Successfully loaded FODT content for paragraphs: " .. include_src)
        -- Return as raw block content that will be interpreted as ODT
        return pandoc.RawBlock("opendocument", body_content)
      end
      
    -- ODF/ODT support removed
    end
  end
  
  return nil
end

-- Handle Para elements that contain include Images - replace entire paragraph with include content
function Para(el)
  -- First, try to detect include fences that Pandoc left as plain text
  -- e.g. ::: {.include src="path/to/file.fodt" alt="desc"} :::
  local para_text = pandoc.utils.stringify(el)
  if para_text and para_text:match(":::%s*{.-%.include") then
    -- Extract the attribute block between braces
    local attrs = para_text:match("{(.-)}")
    if attrs then
      -- Parse src, alt and style attributes (support double/single quotes or unquoted)
      local src = attrs:match('src%s*=%s*"(.-)"') or attrs:match("src%s*=%s*'(.-)'") or attrs:match('src%s*=%s*([^%s"]+)')
      local alt = attrs:match('alt%s*=%s*"(.-)"') or attrs:match("alt%s*=%s*'(.-)'") or attrs:match('alt%s*=%s*([^%s"]+)')
      local style = attrs:match('style%s*=%s*"(.-)"') or attrs:match("style%s*=%s*'(.-)'") or attrs:match('style%s*=%s*([^%s"]+)') or "Default Paragraph Style"

      if src and src ~= "" then
        print("Found textual include src: " .. src)
        -- Try to get paragraphs from the include file
        local include_block = get_include_paragraphs(src)
        if include_block then
          print("Successfully extracted include paragraphs from textual fence: " .. src)
          return include_block
        end

        -- Fallback: use process_include to insert raw ODT content
        local fallback = process_include(src, style, alt or src, "block")
        if fallback then
          return fallback
        end
      end
    end
  end

  -- Check for images without attributes (backward compatibility)
  for i, content in ipairs(el.content) do
    if content.t == "Image" then
      local img = content
      local src = img.src

      -- Check if the image source points to the include directory
      if src and src:match("%.fodt$") then
        print("Processing include image in paragraph: " .. src)
        
        -- Get include content as block
        local include_block = get_include_paragraphs(src)
        if include_block then
          print("Successfully extracted include paragraphs (compatibility mode)")
          return include_block
        else
          print("Failed to extract include content, keeping original paragraph")
          return el
        end
      end
    end
  end

  -- Return the paragraph unchanged if it doesn't contain an include
  return el
end