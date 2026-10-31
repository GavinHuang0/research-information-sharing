-- Keep Markdown links local in GitHub, but make links portable in the PDF.
function Link(link)
  if link.target:match('^%.%./') then
    link.target = 'https://github.com/GavinHuang0/research-information-sharing/blob/main/'
      .. link.target:gsub('^%.%./', '')
  end
  return link
end
