class Plous < Formula
  desc "Kubernetes lifecycle tool for your terminal"
  homepage "https://github.com/simjay/plous"
  url "https://github.com/simjay/plous/archive/refs/tags/v0.0.2.tar.gz"
  sha256 "cdf98410440abac6d8fb0b845cd2e4155c79e6d02e18a63296595565be1e3fe0"
  license "Apache-2.0"

  bottle do
    root_url "https://github.com/simjay/homebrew-tap/releases/download/plous-0.0.2"
    sha256 cellar: :any_skip_relocation, arm64_sequoia: "63a3088247c35d51dc51adbffd595070480279c1ca3a62a99ddf991381f061bc"
    sha256 cellar: :any_skip_relocation, arm64_linux:   "12429a8629278a5ba338a33f40ed352ccaeb3334d80214cf6dcd8bc97732914f"
    sha256 cellar: :any_skip_relocation, x86_64_linux:  "7df8eb087964f4d01d63f2d2fb06c12bb695bac13d890255fb8be684a7f22ced"
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
