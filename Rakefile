# frozen_string_literal: true

# Running locally? Try `bundle exec rake` to avoid conflicts with system ruby

require 'English'
require 'html-proofer'
require 'rspec/core/rake_task'
require 'rubocop/rake_task'
require 'jekyll'

task default: [:test]

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

desc 'Test website with html_proofer'
task :html_proofer do
  puts 'Running html proofer...'.yellow.bold
  HTMLProofer.check_directory(
    '_site/',
    allow_hash_href: 'true',
    check_html: 'true',
    check_opengraph: 'true',
    file_ignore: [%r{_site/amp/.*}], # Ignore AMP. Handled by AMP-Validator
    internal_domains: ['www.kyleniewiada.org'],
    only_4xx: 'true', # Sick of other random http codes.
    url_ignore:
    [
      %r{.*apple.com/.*}, # Apple blocking Travis CI/typhoeus
      %r{.*savaslabs.com/.*}, # SavasLabs blocking Travis CI/typhoeus
      %r{.*/#comment-.*}, # Internal Disqus comments
      %r{.*kodewerx.org/.*}, # This site responses weirdly..
      %r{.*twitter.com/.*}, # This site now hates HTML Proofer
      %r{https://www.kyleniewiada.org/amp/.*} # Interal linked AMP Pages.
    ]
  ).run
end

desc 'Test website AMP validation'
task :amp do
  puts 'Running AMP Validator...'.yellow.bold
  amp_dir = '_site/amp'
  puts 'Listing all files for testing.'.yellow.bold
  # Fail if we didn't find any amp files to test
  system(
    "find #{amp_dir} -iname '*.html'" \
    "| egrep '.*'" \
    '| xargs -L1 amphtml-validator'
  )
  if $CHILD_STATUS.exitstatus.zero?
    puts 'AMP Validator finished successfully.'.green
  else
    puts 'AMP Validator FAILED.'.red.bold
    exit($CHILD_STATUS.exitstatus)
  end
end

desc 'Run RuboCop'
task :rubocop do
  puts 'Running RuboCop Validator...'.yellow.bold
  RuboCop::RakeTask.new
end

desc 'Run all tests except the JSON validator'
task :test do
  Rake::Task['build'].invoke
  Rake::Task['rubocop'].invoke
  Rake::Task['html_proofer'].invoke
  Rake::Task['amp'].invoke
end
