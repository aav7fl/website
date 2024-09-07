module Jekyll
  module StripScriptsFilter
      def strip_scripts(input)
        # Regular expression to match and remove any script blocks 
        # (used when calculating the word count of a post)
        # We use a lazy match to match the smallest possible block of code.
        # gsub is using the multiline flag to match across newlines.
        # gsub replaces all global matches with an empty string.
        input.gsub(/<script type="text\/javascript"(.+?)<\/script>/m, '')
      end
  end
end
  
Liquid::Template.register_filter(Jekyll::StripScriptsFilter)