# frozen_string_literal: true

# Running locally? Try `bundle exec rake` to avoid conflicts with system ruby

require 'jekyll'

task :build, [:options] do |_t, args|
  # Build twice to handle FastImage issue of non-existent images on init build
  puts 'Building site...'.yellow.bold
  args.with_defaults(options: {})
  orig_stdout = $stdout.clone
  $stdout.reopen('/dev/null', 'w')
  Jekyll::Commands::Build.process({})
  $stdout.reopen(orig_stdout)
  Jekyll::Commands::Build.process(args[:options])
end

task :build_watch do
  # Build the site with custom options such as drafts enabled.
  puts 'Building site with drafts...'.yellow.bold
  options = {
    incremental: true,
    show_drafts: true,
    watch: true
  }
  Rake::Task['build'].invoke(options)
end

task :serve do
  puts 'Serving site...'.yellow.bold
  options = {
    incremental: true,
    serving: true,
    show_drafts: true,
    watch: true
  }
  Jekyll::Commands::Serve.process(options)
end

task :clean do
  puts 'Cleaning up _site...'.yellow.bold
  Jekyll::Commands::Clean.process({})
end
