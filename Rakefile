# Running locally? Try `bundle exec rake` to avoid conflicts with system ruby

require 'html-proofer'
require 'jekyll'

task :build do
  buildOptions = {
    future: true,
  }

  # Build twice to handle FastImage issue of non-existent images on init build
  puts 'Building site...'.yellow.bold
  orig_stdout = $stdout.clone
  $stdout.reopen('/dev/null', 'w')
  Jekyll::Commands::Build.process(buildOptions)
  $stdout.reopen(orig_stdout)
  Jekyll::Commands::Build.process(buildOptions)
end

task :serve do
  puts 'Serving site...'.yellow.bold

  buildOptions = {
    future: true,
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
    ignore_urls:
    [
      %r{.*apple.com/.*}, # Apple blocking Travis CI/typhoeus
      %r{.*savaslabs.com/.*}, # SavasLabs blocking Travis CI/typhoeus
      %r{.*/#comment-.*}, # Internal Disqus comments
      %r{https://www.linkedin.com.*}, # They always return a 999
      %r{https://www.reddit.com.*}, # Reddit is blocking us :(
      %r{.*x.com/.*}, # This site now hates HTML Proofer
      %r{https://frenck.dev.*}, # Cloudflare is blocking us :(
      %r{^https://github.com/aav7fl/website/blob/72e003eba56facb762a0bd2ffb79876e5a9e299a/.travis.yml#L23}, # GitHub is saying the anchor is an error
      %r{^https://github.com/home-assistant/core/blob/dd7a06b9dca8a04152f6c4ef4828c8e214260393/homeassistant/components/google_assistant/trait.py#L522-L530} # GitHub is saying the anchor is an error
    ],
    swap_urls: {
      %r{^https://www.kyleniewiada.org/} => '/' # Convert internal links that may not exist yet.
    }
  ).run
end

task :clean do
  puts 'Cleaning up _site...'.yellow.bold
  Jekyll::Commands::Clean.process({})
end

task :default => [:serve]
