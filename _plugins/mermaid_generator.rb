# Replaces Mermaid diagrams with the static SVGs produced by
# scripts/pre-render-mermaid.js.
#
# Both a fenced ```mermaid block and a legacy <div class="mermaid"> block are
# swapped for a plain <img> tag before Jekyll converts the Markdown. The AMP
# layout pipes that <img> through amp-jekyll's `amp_images` filter, which turns
# it into <amp-img layout="responsive"> with the width and height already set,
# so no client-side Mermaid JavaScript is ever loaded.
#
# Diagram SVGs are committed to the repo and catalogued in _data/mermaid.json.
# When that manifest no longer matches the Markdown, this plugin runs the
# pre-render script to resync -- so adding, editing, or deleting a diagram just
# works during `rake build` and `rake serve`. Environments that cannot render
# (no Node, no mermaid-cli, or CI) fall back to the committed SVGs.

require 'cgi'
require 'digest'
require 'json'
require 'set'

module Jekyll
  module Mermaid
    MANIFEST = File.join('_data', 'mermaid.json').freeze

    # Matches a fenced ```mermaid block (group 1) or a legacy
    # <div class="mermaid"> block (group 2). Kept byte-for-byte in sync with
    # DIAGRAM_PATTERN in scripts/pre-render-mermaid.js.
    PATTERN = /^```[ \t]*mermaid[^\n]*\r?\n(.*?)\r?\n?^```[ \t]*$|<div class="mermaid">\r?\n?(.*?)<\/div>/m

    class << self
      # Normalizes diagram source so insignificant whitespace does not change
      # the hash. Must behave identically to `normalize` in the Node script.
      def normalize(text)
        text.gsub("\r\n", "\n")
            .split("\n", -1)
            .map { |line| line.sub(/[ \t]+\z/, '') }
            .join("\n")
            .sub(/\A\n+/, '')
            .sub(/\n+\z/, '')
      end

      def diagram_hash(source, config_hash)
        Digest::SHA256.hexdigest("#{normalize(source)}\n--\n#{config_hash}")[0, 16]
      end
    end

    class Generator < Jekyll::Generator
      # Shells out to the pre-render script when a diagram has no SVG yet, so
      # this cannot claim to be safe-mode compatible.
      safe false
      priority :high

      def generate(site)
        @site = site
        @manifest = load_manifest
        @config_hash = config_hash

        # Recomputed every build. Jekyll reuses one Site (and one generator
        # instance) across `serve` rebuilds, so memoizing documents here would
        # pin the previous build's objects -- whose content this generator has
        # already rewritten -- and every diagram would look deleted.
        docs = all_documents
        sources = docs.each_with_object({}) do |doc, map|
          map[relative_path(doc)] = diagram_sources(doc)
        end

        pre_render(sources)
        docs.each do |doc|
          render_diagrams(doc) unless sources[relative_path(doc)].empty?
        end
      end

      private

      def all_documents
        docs = @site.posts.docs + @site.pages
        @site.collections.each_value { |collection| docs += collection.docs }
        docs.uniq.select { |doc| doc.content.is_a?(String) }
      end

      def relative_path(doc)
        doc.relative_path.to_s.sub(%r{\A/}, '')
      end

      # Mirrors `configHash` in scripts/pre-render-mermaid.js.
      def config_hash
        Digest::SHA256.hexdigest(
          File.read(File.join(@site.source, 'scripts', 'mermaid.config.json'))
        )
      end

      def diagram_sources(doc)
        doc.content.scan(PATTERN).map { |fenced, div| fenced || div }
      end

      # Runs the pre-render script when the manifest no longer matches the
      # Markdown, in either direction: a diagram was added or edited (needs an
      # SVG), or one was deleted (its SVG and manifest entry need to go). This
      # keeps `rake serve` honest -- edit or remove a diagram, save, and the
      # watcher's rebuild reflects it.
      #
      # Skipped in CI, where the SVGs are expected to be committed already and
      # `pre-render-mermaid.js --check` guards against stale ones.
      def pre_render(sources)
        return if ENV['CI']

        # Keyed only by files Jekyll actually loaded. Future-dated posts and
        # drafts are absent here, so their manifest entries are not judged stale.
        used = sources.transform_values do |diagrams|
          diagrams.map { |source| Mermaid.diagram_hash(source, @config_hash) }.to_set
        end

        missing = used.any? { |_source, hashes| hashes.any? { |hash| !@manifest.key?(hash) } }
        deleted = @manifest.any? do |hash, entry|
          used.key?(entry['source']) && !used[entry['source']].include?(hash)
        end
        return unless missing || deleted

        unless File.exist?(File.join(@site.source, 'node_modules', '.bin', 'mmdc'))
          Jekyll.logger.warn 'Mermaid:', 'mermaid-cli is not installed. Run `npm ci` to sync diagrams.'
          return
        end

        Jekyll.logger.info 'Mermaid:', 'Syncing diagrams with the Markdown...'
        unless system('node', File.join('scripts', 'pre-render-mermaid.js'), chdir: @site.source)
          Jekyll.logger.warn 'Mermaid:', 'Pre-rendering failed. Run `npm run mermaid` to see the error.'
          return
        end

        @manifest = load_manifest
        register_static_files
      end

      # Jekyll builds its static file list during `read`, which happens before
      # generators run. An SVG rendered just now is therefore invisible to this
      # build and would not be copied into _site until the next one -- a broken
      # image while `rake serve` is watching. Register the new files here, and
      # drop any the sync just deleted so Jekyll's cleaner takes the stale copy
      # out of _site on this build rather than the next.
      def register_static_files
        @site.static_files.reject! do |file|
          file.relative_path.to_s.match?(/-diagram-\d+\.svg\z/) &&
            !File.exist?(File.join(@site.source, file.relative_path))
        end

        known = @site.static_files.map(&:relative_path).to_set

        @manifest.each_value do |entry|
          next if known.include?(entry['src'])
          next unless File.exist?(File.join(@site.source, entry['src']))

          @site.static_files << Jekyll::StaticFile.new(
            @site, @site.source, File.dirname(entry['src']), File.basename(entry['src'])
          )
        end
      end

      def load_manifest
        path = File.join(@site.source, MANIFEST)
        return {} unless File.exist?(path)

        JSON.parse(File.read(path)).fetch('diagrams', {})
      rescue JSON::ParserError => e
        Jekyll.logger.warn 'Mermaid:', "Could not parse #{MANIFEST}: #{e.message}"
        {}
      end

      def render_diagrams(doc)
        doc.content = doc.content.gsub(PATTERN) do
          source = Regexp.last_match(1) || Regexp.last_match(2)
          hash = Mermaid.diagram_hash(source, @config_hash)
          entry = @manifest[hash]

          if entry.nil?
            Jekyll.logger.warn(
              'Mermaid:',
              "No pre-rendered SVG for a diagram in #{doc.relative_path}. " \
              'Run `npm run mermaid` and commit the result.'
            )
            next ''
          end

          image_tag(entry, hash)
        end
      end

      # A plain <img> keeps the standard layout untouched and gives amp-jekyll
      # everything it needs (width and height) to emit a valid AMP image.
      #
      # The ?v= fingerprint changes only when the diagram source or the Mermaid
      # config changes, since it is the same hash used to cache the render. The
      # SVG filename is stable, so without it an edited diagram keeps its URL:
      # LiveReload sees byte-identical HTML and the browser serves the old image
      # from cache. It busts readers' caches on a redeploy for the same reason.
      def image_tag(entry, hash)
        <<~HTML

          <img class="mermaid-diagram" src="#{entry['src']}?v=#{hash[0, 8]}" width="#{entry['width']}" height="#{entry['height']}" alt="#{CGI.escapeHTML(entry['alt'].to_s)}" />

        HTML
      end
    end
  end
end
