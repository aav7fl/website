module Jekyll
  module StripCodeBlocksFilter
      def strip_code_blocks(input)
        # Regular expression to match and remove code blocks
        # This will only work if the `pre` tag has a class of `highlight`
        # We use a lazy match to match the smallest possible block of code.
        # gsub is using the multiline flag to match across newlines.
        # gsub replaces all global matches with an empty string.
        input.gsub(/<pre class="highlight">(.+?)<\/pre>/m, '')
      end
  end
end
  
Liquid::Template.register_filter(Jekyll::StripCodeBlocksFilter)