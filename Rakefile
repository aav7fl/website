# Running locally? Try `bundle exec rake` to avoid conflicts with system ruby

require 'html-proofer'
require 'jekyll'

desc 'Pre-render Mermaid diagrams to static SVGs'
task :mermaid do
  script = File.join('scripts', 'pre-render-mermaid.js')

  unless system('node', '--version', out: File::NULL, err: File::NULL)
    puts 'Node.js not found. Skipping Mermaid pre-render.'.yellow
    next
  end

  # Render when we can. Environments without mermaid-cli, or with a Node too old
  # to run it (some dev containers), fall back to verifying that every diagram
  # already has an up-to-date SVG committed -- which is all a build really needs.
  next if File.exist?(File.join('node_modules', '.bin', 'mmdc')) && system('node', script)

  puts 'Could not pre-render Mermaid diagrams here; checking committed SVGs instead.'.yellow
  next if system('node', script, '--check')

  abort 'Mermaid diagrams are missing or out of date. Render them where mermaid-cli works (`npm ci && npm run mermaid`) and commit the SVGs plus _data/mermaid.json.'.red
end

task :build => :mermaid do
  buildOptions = {
    future: true,
  }

  # Force site into production mode under this step to ensure comments and analytics are enabled.
  ENV['JEKYLL_ENV'] = 'production'

  # Build twice to handle FastImage issue of non-existent images on init build
  puts 'Building site...'.yellow.bold
  orig_stdout = $stdout.clone
  $stdout.reopen('/dev/null', 'w')
  Jekyll::Commands::Build.process(buildOptions)
  $stdout.reopen(orig_stdout)
  Jekyll::Commands::Build.process(buildOptions)
end

task :serve => :mermaid do
  puts 'Serving site...'.yellow.bold

  # `open_url` below asks the OS to open a browser. Inside a dev container that
  # routes through VS Code's CLI shim, which calls the deprecated url.parse()
  # and prints a DEP0169 warning on every start. It is VS Code's code, not ours,
  # so silence just that one code for the processes this task spawns.
  ENV['NODE_OPTIONS'] =
    [ENV['NODE_OPTIONS'], '--disable-warning=DEP0169'].compact.join(' ').strip

  buildOptions = {
    future: true,
    incremental: true,
    watch: true,
    # Lets Build.process start the watcher and return, instead of blocking
    # forever, so the server can be started on this same thread afterwards.
    serving: true,
  }

  serveOptions = {
    host: "0.0.0.0",
    livereload: true,
    livereload_port: 35729,
    open_url: true,
  }

  # Jekyll builds the URL it opens (and logs) from the bind address, giving
  # http://0.0.0.0:3000, which VS Code then opens as 127.0.0.1. Show and open
  # localhost instead -- same server, friendlier URL.
  Jekyll::Commands::Serve.singleton_class.prepend(Module.new do
    def server_address(server, options = {})
      super.sub('://0.0.0.0:', '://localhost:')
    end
  end)

  # Build twice for the same reason :build does: FastImage can only read the
  # dimensions of images that already exist in _site, so the AMP layout gets
  # them on the second pass. Serve.process only starts the web server -- it
  # never builds -- so both passes have to happen here. A _site left over from
  # an earlier run already has the images, so skip the extra ~10s pass then.
  Jekyll::Commands::Build.process(future: true) unless Dir.exist?('_site/assets')
  Jekyll::Commands::Build.process(buildOptions)
  Jekyll::Commands::Serve.process(serveOptions)
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
    ignore_status_codes: [
      502, 
      503
    ], # Ignore common errors
    ignore_urls:
    [
      %r{.*amp.dev/.*}, # Blocks too many requests at once like re-runs
      %r{.*apple.com/.*}, # Apple blocking Travis CI/typhoeus
      %r{.*cchsmi.com/*}, # They've started returning a 403 to us
      %r{.*ebird.org/.*}, # eBird is blocks us :(
      %r{.*loc.gov/.*}, # Seems to break every other day
      %r{.*opensprinkler.com/.*}, # Returns a 403
      %r{.*savaslabs.com/.*}, # SavasLabs blocking Travis CI/typhoeus
      %r{.*uplink.nmu.edu/.*}, # They've started returning a 403 to us
      %r{.*/#comment-.*}, # Internal Disqus comments
      %r{^https://bluecharmbeacons.com/}, # Returns a 403
      %r{^https://boardgamegeek.com/}, # Returns a 403
      %r{^https://fcc.report/}, # Blocking us now
      %r{^https://linktr.ee/}, # Returns a 406
      %r{^https://merlin.allaboutbirds.org.*}, # Returns a 403
      %r{^https://www.androidauthority.com.*}, # 403s
      %r{^https://www.audiokarma.org.*}, # 403s
      %r{^https://www.howtogeek.com.*}, # 403s
      %r{^https://www.linkedin.com.*}, # They always return a 999
      %r{^https://www.raspberrypi.com.*}, # 403s
      %r{^https://www.reddit.com.*}, # Reddit is blocking us :(
      %r{^https://www.sweetscape.com/}, # Returns response code 0???
      %r{^https://www.thingiverse.com/}, # 403s
      %r{^https://zeldaspeedruns.wikia.com/}, # Returns a 403
      %r{.*x.com/.*}, # This site now hates HTML Proofer
      %r{^https://frenck.dev.*}, # Cloudflare is blocking us :(
      %r{^https://github.com/aav7fl/website/blob/72e003eba56facb762a0bd2ffb79876e5a9e299a/.travis.yml#L23}, # GitHub is saying the anchor is an error
      %r{^https://github.com/home-assistant/core/blob/dd7a06b9dca8a04152f6c4ef4828c8e214260393/homeassistant/components/google_assistant/trait.py#L522-L530}, # GitHub is saying the anchor is an error
      %r{^https://github.com/Koenkk/zigbee2mqtt/issues/23661#issuecomment-3843098714}, # GitHub is saying the anchor is an error
      %r{^https://kyleniewiada.bandcamp.com/}, # Returns a 403
      %r{^https://scoresaber.com/}, # 403s
      %r{^https://sooeveningnews.newsbank.com/.*}, # NewsBank thinks we're a bot if we test too often
      %r{^https://travis-ci.com/*}, # Blocked with 415
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

# Lives outside the workspace: Jekyll's file watcher walks every directory in
# the repo (its excludes only filter events), and torch's ~2,500 directories
# over the bind mount added ~45s to every `rake serve` start.
BIRDS_PYTHON = '/opt/venv-birds/bin/python'

def run_birds_script(script, *default_args, forward_extra: true)
  extra_args = if forward_extra
                 args = ARGV.drop_while { |arg| arg != '--' }.drop(1)
                 args.each { |arg| task(arg.to_sym) {} unless Rake::Task.task_defined?(arg) }
                 args
               else
                 []
               end
  sh(BIRDS_PYTHON, "scripts/birds/#{script}", *default_args, *extra_args) do |ok, status|
    next if ok

    if status&.signaled?
      sig = status.termsig
      name = Signal.signame(sig) || sig.to_s
      exit(128 + sig) if name == 'INT'
      hint = if name == 'KILL'
               ' (usually out of memory in the container; check `ps aux` for a leftover python process or restart the container)'
             else
               ''
             end
      abort "scripts/birds/#{script} was killed by signal #{sig} (SIG#{name})#{hint}"
    end
    exit(status&.exitstatus || 1)
  end
end

namespace :birds do
  desc "Set up offline data: eBird codes, ABA checklist, the pinned AI model and its embeddings (safe to re-run)"
  task :setup do
    run_birds_script('setup_offline_assets.py')
  end

  # Options after "--" go to the migration, e.g. -- --yes
  desc "After an eBird taxonomy update: rebuild taxonomy_sibley.csv, migrate the catalog to it (renames, splits), rebuild embeddings"
  task :update_taxonomy do
    run_birds_script('setup_offline_assets.py', '--refresh-taxonomy', '--skip-models', forward_extra: false)
    run_birds_script('migrate_taxonomy.py')
    run_birds_script('setup_offline_assets.py', forward_extra: false)
  end

  desc "Update _data/birds.yml to the current taxonomy_sibley.csv (options after --, e.g. -- --check or -- --yes)"
  task :migrate_taxonomy do
    run_birds_script('migrate_taxonomy.py')
  end

  desc "Import photos from _staging/ into assets/img/birds/ and _data/birds.yml (options after --, e.g. -- --americas)"
  task :import do
    run_birds_script('import_birds.py')
  end

  desc "Report (or, with -- --apply, remove) old bird photo versions from git history. Rewrites history!"
  task :compact_history do
    run_birds_script('compact_history.py')
  end

  desc "Run auto-ingestion for high-confidence AI matches (>90%)"
  task :auto do
    run_birds_script('import_birds.py', '--auto')
  end

  desc "Update the bird pipeline's Python packages now (only switches if the new versions pass the checks)"
  task :update_deps do
    run_birds_script('update_deps.py')
  end

  desc "Check every bird pipeline dependency and explain how to fix anything broken"
  task :doctor do
    run_birds_script('doctor.py')
  end

  desc "Run the bird pipeline's unit test suite"
  task :test do
    sh BIRDS_PYTHON, '-m', 'unittest', 'discover', '-s', 'scripts/birds', '-p', 'test_*.py', '-v'
  end

  desc "Measure the AI model's accuracy on the catalog photos (try a candidate with -- --model-dir DIR)"
  task :evaluate do
    run_birds_script('evaluate_model.py')
  end

  desc "Write copyright tags into every already-imported bird photo"
  task :copyright do
    run_birds_script('import_birds.py', '--stamp-copyright')
  end

  desc "Force re-import of all photos in _staging/"
  task :reimport do
    run_birds_script('import_birds.py', '--force')
  end
end
