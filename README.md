# WEBAPP
- [WEBAPP](#webapp)
  - [Overview](#overview)
  - [Installation](#installation)
    - [Installation via Ansible](#installation-via-ansible)
      - [Prerequisites](#prerequisites)
      - [Preparations](#preparations)
      - [Running the playbook](#running-the-playbook)
    - [Manual installation](#manual-installation)
  - [API guide](#api-guide)
  - [Testing webapp locally with provided demo resources](#testing-webapp-locally-with-provided-demo-resources)

## Overview
This is a simple proof-of-concept Python Flask application **webapp** that can be used for monitoring the statuses of other applications. webapp is set up with Docker compose and it exposes an API that can be used for communicating with the application. This API can be used for obtaining or updating the status of some application via HTTP requests. These requests can be done manually, but it is also possible to use webapp API as a webhook for some other platform. For example, it can be used as a contact point for Grafana alerts.

The webapp setup consists of three Docker containers running in webapp Docker network. Here is a very simple diagram of the architecture:

![alt text](webapp.png)

In total, there are three services in the webapp Docker compose setup:

- **nginx**

    nginx is used as a proxy that forwards HTTP requests to the webapp. Using nginx in front of webapp helps to keep Flask logic simpler as more complex web server configuration can be handled by nginx. nginx is the only container that is reachable from outside of the webapp Docker network as it is bound to the configured host port. Communication with other services is contained within webapp Docker network.
- **webapp**

    webapp is the Python Flask application that handles the API logic. webapp executes various SQL queries based on the incoming HTTP API requests to insert or display information about some application's health. webapp uses PostgreSQL as its database.

- **webapp-postgres**

    webapp-postgres provides PostgreSQL database service to webapp. In the proof-of-concept version described in this README, webapp-postgres database consists of one table **monitoring** that has three columns:
    - id ---> serial
    - appname (**primary key**) ---> varchar(255)
    - status ---> varchar(7) 

## Installation
This repository contains two options that can be used for installing webapp:

### Installation via Ansible
Ansible playbook **webapp.yaml** can be used for automatically setting up webapp locally, all necessary files can be found from directory **ansible**.  

#### Prerequisites
Installing webapp via Ansible has some prerequisites that need to met for the playbook run to be successful:

- Hosts defined in **webapp** host group must have docker and docker compose installed. The prepared **./ansible/hosts** file is using localhost as the target.
- Hosts defined in **webapp** host group must have pip3 installed
- The host that is used for running the playbook must have **community.docker** version 3.7.0 ansible collection installed. This is needed for Docker compose V2 Ansible module. The ansible package installation often comes with an older version of **community.docker** collection, but the version can be upgraded with command 
    ```
    ansible-galaxy collection install community.docker
    ```
- The configured user for **webapp** hosts must have necessary permissions for executing docker commands. If no user is explicitly defined for **webapp** hosts, then Ansible will use the user that is executing the playbook by default.

#### Preparations
Before the playbook can be executed, following preparations need to be done:

- The prepared variable files in ./ansible/group_vars are using Ansible Vault for storing sensitive data. If you also wish to use Ansible Vault, create Vault password file **~/.ansible/vault_password** (defined in **./ansible/ansible.cfg**). Local testing can be done without encrypted secrets as well, so feel free to skip the encryption part and define plaintext values for the variables described in the next step.
- Generate encrypted values for variables **localhost_become_password** (this is the password for localhost user running the playbook, needed for executing some tasks with root permissions), **webapp_pg_user** (this username will be used for creating a database user for webapp) and **webapp_pg_secret** (password for webapp database user) with command:
    ```
    ansible-vault --vault-password-file ~/.ansible/vault_password encrypt_string '<string_to_encrypt>' --name '<string_name_of_variable>' 
    ```
    **localhost_become_password** should be added to **/ansible/group_vars/all.yaml** file, other two variables should be added to **./ansible/group_vars/webhosts.yaml**.
- Define value for variable **webapp_user** (location **./ansible/group_vars/webhosts.yaml**). This user will be configured as the owner of files related to webapp.
#### Running the playbook
If the preparations have been done, then it is possible to run the playbook: 
```
   ansible-playbook webapp.yaml
```

Here is a little summary about what the playbook will do:

1. First play just gathers information about the hosts (the provided Ansible setup only uses localhost)
2. Second play will prepare and start up webapp:
   1. By default, all files related to webapp will be added to **/var/lib/webapp**. This location can be overridden by defining some other location with variable **webapp_root_dir** in **./ansible/group_vars/webapp.yaml**
   2. By default, Ansible will build webapp Docker image locally and will use the locally built image in the Docker compose file. This task can be skipped by setting variable **do_build** to false in **./ansible/group_vars/webapp.yaml**
   3. By default, Ansible will use image name **webapp** and tag **v1.0**. These can be changed by defining variables **webapp_image_name** and **webapp_image_version** in **./ansible/group_vars/webapp.yaml**. 
   4. By default, webapp will be exposed to the public with domain name **webapp.demo**. This domain name can be changed by defining variable **webapp_domain** in **./ansible/group_vars/webapp.yaml**
   5. By default, nginx will bind to host port 8080. This can be changed by defining variable **webapp_host_port** in **./ansible/group_vars/webapp.yaml**.
   6. The prepared Ansible setup is meant for starting up proof-of-concept version of webapp locally. Therefore it assumes that system wide DNS hasn't been set up for webapp domain and adds an entry to /etc/hosts file to resolve the webapp domain name. This task can be skipped by setting variable **local_testing** to false in **./ansible/group_vars/webapp.yaml**
3. Third play is optional and is disabled by default. If it is enabled, then the third play will prepare and start up resources that can be used for testing webapp. More details about these demo resources and testing webapp can be found below.

When the playbook has finished, then it should be possible to access webapp via URLs http://localhost:HOSTPORT (http://localhost:8080 by default) and http://WEBAPPDOMAIN:HOSTPORT (http://webapp.demo:8080 by default). Following message and web page should be shown, if webapp is up and running: 
![alt text](webapp_up.PNG)

Check the API guide below to see how to communicate with webapp.

### Manual installation
Another option for installing webapp is deploying it manually. All necessary files can be found from directory **manual-deploy**. Following steps need to be done to perform manual installation of webapp:
- Copy the manual-deploy directory to a suitable destination 
- Configure database user for webapp by writing the username to file **./manual-deploy/config/pg_user**. This file will be used to create Docker secret **pg-user** that webapp and webapp-postgres services are using.
- Configure database password for webapp by writing the password to file **./manual-deploy/config/pg_secret**. This file will be used to create Docker secret **pg-secret** that webapp and webapp-postgres services are using.
- Start up the Docker compose setup in detached mode with command while being in the directory:
```
   docker compose up -d
```
The Docker compose file will build webapp image based on Dockerfile located in the directory and will start up all services. After docker compose command has finished, webapp should be accessible via URL http://localhost:8080 and display following message:
![alt text](manual_install_test.PNG)

If you wish to test accessing webapp via the domain name defined in nginx configuration, add a corresponding entry to /etc/hosts file (should refer to IPv4 address of the local machine). By default, domain **webapp.demo** will be used, making the webapp accessible via URL http://webapp.demo:8080. If you wish to change webapp domain, change the default **server_name** parameter in **./manual-deploy/config/webapp-nginx.conf** to the preferred value and execute following command inside the manual installation directory:
```
   docker compose restart
```
Check the API guide below to see how to communicate with webapp.

## API guide

## Testing webapp locally with provided demo resources