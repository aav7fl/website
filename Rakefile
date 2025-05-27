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
      %r{.*apple.com/.*},
      %r{.*ebird.org/.*},
      %r{.*loc.gov/.*},
      %r{.*opensprinkler.com/.*},
      %r{.*savaslabs.com/.*},
      %r{.*uplink.nmu.edu/.*},
      %r{.*/#comment-.*}, # Disqus comments
      %r{https://www.linkedin.com.*},
      %r{https://www.reddit.com.*},
      %r{.*x.com/.*},
      %r{^https://frenck.dev.*},
      %r{^https://github.com/aav7fl/website/blob/.*},
      %r{^https://github.com/home-assistant/core/.*},
      %r{^https://sooeveningnews.newsbank.com/.*}
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
