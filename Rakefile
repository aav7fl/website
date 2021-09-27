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

task :serve do
  puts 'Serving site...'.yellow.bold

  buildOptions = {
    incremental: true,
    watch: true,
  }
  
  serveOptions = {
    livereload: true,
    livereload_port: 35729,
    open_url: true,
  }

  build = Thread.new { Jekyll::Commands::Build.process(buildOptions) }
  serve = Thread.new { Jekyll::Commands::Serve.process(serveOptions) }

  commands = [build, serve]
  commands.each { |c| c.join }
end

task :clean do
  puts 'Cleaning up _site...'.yellow.bold
  Jekyll::Commands::Clean.process({})
end

task :default => [:serve]