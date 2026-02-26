# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure("2") do |config|
  # 使用 Ubuntu 22.04 LTS
  config.vm.box = "ubuntu/jammy64"
  config.vm.hostname = "semiconductor-monitor"

  # 埠轉發：Host → VM
  # FastAPI 後端
  config.vm.network "forwarded_port", guest: 8100, host: 8100, host_ip: "127.0.0.1"
  # Streamlit 前端
  config.vm.network "forwarded_port", guest: 8601, host: 8601, host_ip: "127.0.0.1"

  # 同步專案目錄到 VM
  config.vm.synced_folder ".", "/home/vagrant/app"

  # VM 資源設定
  config.vm.provider "virtualbox" do |vb|
    vb.name   = "semiconductor-monitor-vm"
    vb.memory = "2048"
    vb.cpus   = 2
  end

  # 執行 provision 腳本
  config.vm.provision "shell", path: "provision.sh"

  # 每次 vagrant up/reload 時自動啟動服務
  config.vm.provision "shell", run: "always", inline: <<-SHELL
    echo "啟動半導體監控服務..."
    sudo systemctl start semiconductor-monitor.service || true
  SHELL
end
