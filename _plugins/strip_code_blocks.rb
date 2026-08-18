module Jekyll
  module StripCodeBlocksFilter
      def strip_code_blocks(input)
        # Regular expressions to match and remove code blocks
        # Fenced blocks give us a `pre` tag with a class of `highlight`, while
        # the `highlight` tag wraps a plain `pre` in a `figure` instead.
        # We use a lazy match to match the smallest possible block of code.
        # gsub is using the multiline flag to match across newlines.
        # gsub replaces all global matches with an empty string.
        input.gsub(/<pre class="highlight">(.+?)<\/pre>/m, '')
             .gsub(/<figure class="highlight">(.+?)<\/figure>/m, '')
      end
  end
end
  
Liquid::Template.register_filter(Jekyll::StripCodeBlocksFilter)