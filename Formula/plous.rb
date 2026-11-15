class Plous < Formula
  desc "Kubernetes lifecycle tool for your terminal"
  homepage "https://github.com/simjay/plous"
  url "https://github.com/simjay/plous/archive/refs/tags/v0.0.5.tar.gz"
  sha256 "25e531b7736bc4a0eea4f067598954e3251b7c375983a5eefc80f523ac871c68"
  license "Apache-2.0"

  bottle do
    root_url "https://github.com/simjay/homebrew-tap/releases/download/plous-0.0.5"
    sha256 cellar: :any_skip_relocation, arm64_sequoia: "d54538217758b1fe98e5d70029f77a993cdde1d7953b98bb3820ffd0fa07d749"
    sha256 cellar: :any_skip_relocation, arm64_linux:   "e3f24cf61f0aa053a10d0b86b1333a5e9c1b83d8c27dd5eb14f8ed19a06a1fee"
    sha256 cellar: :any_skip_relocation, x86_64_linux:  "9fd614030cb144620e491b66e928f2ac73e322982cc2aa4342b8ccbd8659a8ef"
  end

  depends_on "go@1.26" => :build

  def install
    ENV["CGO_ENABLED"] = "0"
    system "go", "build", *std_go_args, "-buildvcs=false", "./cmd/plous"
  end

  test do
    assert_equal version.to_s, shell_output("#{bin}/plous --version").strip
    assert_match "-data-dir", shell_output("#{bin}/plous --help 2>&1")
    assert_match "interactive terminal", shell_output("#{bin}/plous --data-dir #{testpath}/state 2>&1", 1)
    refute_path_exists testpath/"state"

    require "io/console"
    require "pty"
    require "timeout"

    (testpath/"kubeconfig").write <<~YAML
      apiVersion: v1
      kind: Config
      clusters: []
      contexts: []
      users: []
    YAML
    ENV["KUBECONFIG"] = (testpath/"kubeconfig").to_s
    ENV["TERM"] = "xterm-256color"
    PTY.spawn((bin/"plous").to_s, "--data-dir", (testpath/"session").to_s) do |reader, writer, pid|
      reader.winsize = [40, 120]
      waited = false
      begin
        Timeout.timeout(30) do
          output = +""
          output << reader.readpartial(8192) until output.include?("Current Workspace")
          writer.write("\u0003")
          begin
            loop { reader.readpartial(8192) }
          rescue EOFError, Errno::EIO
            # PTY closure differs between macOS and Linux.
          end
          _, status = Process.wait2(pid)
          waited = true
          assert_predicate status, :success?
        end
      ensure
        unless waited
          Process.kill("KILL", pid)
          Process.wait(pid)
        end
      end
    end
  end
end
