-- Keep Markdown links local in GitHub, but make links portable in the PDF.
function Link(link)
  if link.target:match('^%.%./') then
    link.target = 'https://github.com/GavinHuang0/research-information-sharing/blob/main/'
      .. link.target:gsub('^%.%./', '')
  end
  return link
end

-- Markdown displays existing PNGs; the PDF embeds their vector counterparts.
function Image(image)
  if image.src:match('^%.%./results/') then
    image.src = image.src:gsub('%.png$', '.pdf')
    image.attributes.width = '100%'
  end
  return image
end

-- HTML comments are invisible on GitHub and delimit landscape PDF pages.
function RawBlock(block)
  if block.format == 'html' then
    if block.text == '<!-- progress-landscape-begin -->' then
      return pandoc.RawBlock('latex', '\\clearpage\n\\begin{landscape}')
    elseif block.text == '<!-- progress-landscape-next -->' then
      return pandoc.RawBlock('latex', '\\clearpage')
    elseif block.text == '<!-- progress-landscape-end -->' then
      return pandoc.RawBlock('latex', '\\end{landscape}')
    end
  end
end
