# -*- mode: ruby -*-
# vi: set ft=ruby :

require 'yaml'

VAGRANTFILE_DIR = File.dirname(__FILE__)

Vagrant.configure("2") do |config|
  vm_boxes = {
    "centos7" => "centos/7",
    "centos6" => "centos/6",
    "debian9" => "debian/stretch64",
    "fedora25" => "fedora/25-cloud-base",
    "opensuse42.2" => "opensuse/openSUSE-42.2-x86_64",
  }

  extra_boxes_loaded = false

  # allows us to share base boxes with Katello/forklift
  base_boxes = Dir.glob "#{VAGRANTFILE_DIR}/vagrant/plugins/*/base_boxes.yaml"
  base_boxes.each do |file|
    boxes = YAML.load_file(file)
    boxes.each do |name, config|
      if config.has_key? 'libvirt' and not name.include? 'sat'
        vm_boxes[name] = config['libvirt']
        extra_boxes_loaded = true
      end
    end
  end

  primary_vm = "centos7"

  config.vm.provider "libvirt"  # prefer libvirt

  # forward X11 by default
  config.ssh.forward_x11 = true

  # setup shared folder
  config.vm.synced_folder ".", "/vagrant", type: "rsync", rsync__exclude: [
    "build",
    "src/rhsm/_certificate.so",
    "subscription-manager.egg-info",
    "cockpit/node_modules",
    "updates.img",
    "vagrant/vagrant_data",
  ]

  # Set up the hostmanager plugin to automatically configure host & guest hostnames
  if Vagrant.has_plugin?("vagrant-hostmanager")
    config.hostmanager.enabled = true
    config.hostmanager.manage_host = true
    config.hostmanager.manage_guest = true
    config.hostmanager.include_offline = true
  end

  vm_boxes.each do |name, box|
    is_primary = name == primary_vm
    config.vm.define name, autostart: is_primary, primary: is_primary do |host|
      host.vm.host_name = "#{name}.subman.example.com"
      host.vm.box = box
      host.vm.provider :libvirt do |domain|
        domain.graphics_type = "spice"
        domain.video_type = "qxl"
        domain.memory = 1024
      end
      host.vm.provider :virtualbox do |domain, override|
        override.vm.network "forwarded_port", guest: 9090, host: 9090  # allow VirtualBox to serve cockpit over 9090
      end
    end
  end

  ['SUBMAN_RHSM_USERNAME', 'SUBMAN_RHSM_PASSWORD'].each do |var|
    if extra_boxes_loaded and not ENV.include? var
      puts "#{var} not defined. Expect failures. Please set up environment accordingly, and run `vagrant provision`. to correct"
    end
  end

  config.vm.provision "ansible", run: "always" do |ansible|
    ansible.playbook = "vagrant/vagrant.yml"
    ansible.groups = {
      "subman-devel" => vm_boxes.keys()
    }
    ansible.extra_vars = {
      "subman_checkout_dir" => "/vagrant",
      "subman_setup_hacking_environment" => "true",
      "subman_add_vagrant_candlepin_to_hosts" => "true",
    }
    # This will pass any environment variables beginning with "SUBMAN_" or
    # "subman_" (less the prefix) along with their values to ansible for
    # use in our playbooks.
    #
    # Check the playbooks to see how these variables are used.
    env_prefix = "subman_"
    ENV.each do |key, value|
      if key.downcase.start_with?(env_prefix)
          new_var_key = key.downcase()
          ansible.extra_vars[new_var_key] = value
      end
    end
  end
end

# We need to specify static IP address, because this IP address has to be part
# of private network configuration, see: libvirt__dhcp_bootp_server: ip_addr
ip_addr_server = '192.168.111.5'
ip_prefix = '24'

Vagrant.configure("2") do |config|
  config.ssh.forward_x11 = true

  config.vm.network "private_network",
    ip: ip_addr_server,
    auto_config: false,
    libvirt__dhcp_bootp_file: 'pxelinux.0',
    libvirt__dhcp_bootp_server: ip_addr_server,
    libvirt__network_name: 'pxe-server0'

  # PXE server
  config.vm.define 'pxe-server', autostart: false do |host|
    host.vm.hostname = 'pxe-server'
    host.vm.box = 'centos/7'

    host.vm.provision "ansible", run: "always" do |ansible|
      ansible.playbook = "vagrant/vagrant_pxe_server.yml"
      ansible.groups = {
        "pxe-servers" => [
          "pxe-server"
        ]
      }
      ansible.extra_vars = {
        "pxe_server_ip_addr" => ip_addr_server + '/' + ip_prefix
      }
    end
  end

  # PXE client
  config.vm.define 'pxe-client', autostart: false do |host|
    host.vm.hostname = 'pxe-client'
    host.ssh.username = 'root'
    host.vm.provider :libvirt do |domain|
      boot_network = {'network' => 'pxe-server0'}
      domain.memory = 2048
      domain.storage :file, :size => '20G', :type => 'qcow2'
      domain.boot boot_network
    end
  end
end
