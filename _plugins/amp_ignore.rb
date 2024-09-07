module Jekyll
  module AmpIgnoreFilter
      def amp_ignore(input)
        # Regular expression to match and remove anything in the 
        # {amp_ignore_start} and {amp_ignore_end} tags. 
        # Useful for my AMP pages.
        input.gsub(/{start_amp_ignore}(.*?){end_amp_ignore}/m, '')
      end
  end
end

module Jekyll
  module AmpUnignoreFilter
      def amp_unignore(input)
        # Regular expression to match and remove just the ignore tags. 
        # Nothing else. Needed in my standard layout.
        # It's stupid. But it's late and I can't think of a better way to remove 
        # the capture tag groups since filters apply to it all the time. 
        # And I only want this to apply when I use it and only for the AMP layout..
        # Which I'm sure Google will kill off in another year or so. Mark these words.
        input.gsub(/{start_amp_ignore}|{end_amp_ignore}/m, '')
      end
  end
end
  
Liquid::Template.register_filter(Jekyll::AmpIgnoreFilter)
Liquid::Template.register_filter(Jekyll::AmpUnignoreFilter)