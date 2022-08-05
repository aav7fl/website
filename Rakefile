# Running locally? Try `bundle exec rake` to avoid conflicts with system ruby

require 'html-proofer'
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
    host: "0.0.0.0",
    livereload: true,
    livereload_port: 35729,
    open_url: true,
  }

  build = Thread.new { Jekyll::Commands::Build.process(buildOptions) }
  serve = Thread.new { Jekyll::Commands::Serve.process(serveOptions) }

  commands = [build, serve]
  commands.each { |c| c.join }
end

desc 'Test website with html_proofer'
task :html_proofer do
  puts 'Running html proofer...'.yellow.bold
  HTMLProofer.check_directory(
    '_site/',
    allow_hash_href: 'true',
    check_html: 'true',
    check_opengraph: 'true',
    ignore_files: [%r{_site/amp/.*}], # Ignore AMP. Handled by AMP-Validator
    internal_domains: ['www.kyleniewiada.org'],
    ignore_urls:
    [
      %r{.*apple.com/.*}, # Apple blocking Travis CI/typhoeus
      %r{.*savaslabs.com/.*}, # SavasLabs blocking Travis CI/typhoeus
      %r{.*/#comment-.*}, # Internal Disqus comments
      %r{https://www.linkedin.com.*}, # They always return a 999
      %r{.*twitter.com/.*}, # This site now hates HTML Proofer
      %r{https://frenck.dev.*} # Cloudflare is blocking us :(
    ],
    typhoeus: {
      followlocation: true,
      connecttimeout: 30,
      timeout: 30 
    }
  ).run
end

task :clean do
  puts 'Cleaning up _site...'.yellow.bold
  Jekyll::Commands::Clean.process({})
end

task :default => [:serve]
