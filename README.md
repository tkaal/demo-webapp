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
    - [Root endpoint](#root-endpoint)
    - [Adding a new application to webapp's database](#adding-a-new-application-to-webapps-database)
    - [List all items in webapp database](#list-all-items-in-webapp-database)
    - [List details about a specific item in webapp database](#list-details-about-a-specific-item-in-webapp-database)
    - [Get status of a specific item in webapp database](#get-status-of-a-specific-item-in-webapp-database)
    - [Update the status of a specific item in webapp database](#update-the-status-of-a-specific-item-in-webapp-database)
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
Installing webapp via Ansible has some prerequisites that need to be met for the playbook run to be successful:

- Hosts defined in **webapp** host group must have docker and docker compose installed. The prepared **./ansible/hosts** file is using localhost as the target.
- Hosts defined in **webapp** host group must have pip3 installed
- The host that is used for running the playbook must have **community.docker** version 3.7.0 ansible collection installed. This is needed for Docker compose V2 Ansible module. The ansible package installation often comes with an older version of **community.docker** collection, but the version can be upgraded with command 
    ```
    ansible-galaxy collection install community.docker --upgrade
    ```
- The configured user for **webapp** hosts must have necessary permissions for executing docker commands. If no user is explicitly defined for **webapp** hosts, then Ansible will use the user that is executing the playbook by default.

#### Preparations
Before the playbook can be executed, following preparations need to be done:

- The prepared variable files in **./ansible/group_vars** are using Ansible Vault for storing sensitive data. If you also wish to use Ansible Vault, create Vault password file **~/.ansible/vault_password** (defined in **./ansible/ansible.cfg**). Local testing can be done without encrypted secrets as well, so feel free to skip the encryption part and define plaintext values for the variables described in the next step.
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
   6. The prepared Ansible setup is meant for starting up proof-of-concept version of webapp locally. Therefore it assumes that system-wide DNS hasn't been set up for webapp domain and adds an entry to /etc/hosts file to resolve the webapp domain name. This task can be skipped by setting variable **local_testing** to false in **./ansible/group_vars/webapp.yaml**
3. Third play is optional and is disabled by default. If it is enabled, then the third play will prepare and start up resources that can be used for testing webapp. More details about these demo resources and testing webapp can be found below.

When the playbook has finished, then it should be possible to access webapp via URLs http://localhost:HOSTPORT (http://localhost:8080 by default) and http://WEBAPPDOMAIN:HOSTPORT (http://webapp.demo:8080 by default). Following message and web page should be shown, if webapp is up and running: 
![alt text](webapp_up.PNG)

Check the API guide below to see how to communicate with webapp.

### Manual installation
Another option for installing webapp is deploying it manually. All necessary files can be found from directory **manual-deploy**. Following steps need to be done to perform manual installation of webapp:
- Copy the manual-deploy directory to a suitable destination 
- Configure database user for webapp by writing the username to file **./manual-deploy/config/pg_user**. This file will be used to create Docker secret **pg-user** that webapp and webapp-postgres services are using.
- Configure database password for webapp by writing the password to file **./manual-deploy/config/pg_secret**. This file will be used to create Docker secret **pg-secret** that webapp and webapp-postgres services are using.
- Start up the Docker compose setup in detached mode while being in the directory:
```
   docker compose up -d
```
The Docker compose file will build webapp image based on the provided Dockerfile and will start up all services. After docker compose command has finished, webapp should be accessible via URL http://localhost:8080 and display following message:

![alt text](manual_install_test.PNG)

If you wish to test accessing webapp via the domain name defined in nginx configuration, add a corresponding entry to /etc/hosts file (should refer to IPv4 address of the local machine). By default, domain **webapp.demo** will be used, making the webapp accessible via URL http://webapp.demo:8080. If you wish to change webapp domain, change the default **server_name** parameter in **./manual-deploy/config/webapp-nginx.conf** to the preferred value.
Check the API guide below to see how to communicate with webapp.

## API guide
In total, webapp exposes six API endpoints:
### Root endpoint
Root endpoint displays a greeting message if webapp is up and accessible.
```
 http://<webapp_domain>:<webapp_host_port>
```
Sending a HTTP request to root endpoint via CLI:
```
teele@sk-demo:~$ curl http://webapp.demo:8080
Hello there! Demo web app is alive! 
```
Accessing root endpoint via browser:

![alt text](webapp_up.PNG)
### Adding a new application to webapp's database
Following webapp API endpoint can be used for adding a new application to webapp's database via HTTP POST request:
```
http://<webapp_domain>:<webapp_port>/insert-item
```
The API endpoint is expecting a HTTP POST request with json body that contains key **appname**. Value of json key **appname** will be used to insert the new item to webapp's database table. Keep in mind that webapp database uses **appname** column as the primary key meaning that no duplicates are allowed.

If the POST request is successful, then webapp will respond with a success message (e.g. adding new item **testikene** to webapp database):
```
teele@sk-demo:~$ curl -X POST http://webapp.demo:8080/insert-item -H 'Content-Type: application/json' -d '{"appname": "testikene"}'
Successfully added new application testikene to monitoring table! 
```
If the POST request fails, then webapp will respond with a general failure message:
```
teele@sk-demo:~$ curl -X POST http://webapp.demo:8080/insert-item -H 'Content-Type: application/json' -d '{"appname": "testikene"}'
Encountered an error while adding new application testikene to monitoring table 
```
webapp container logs can be checked to see what went wrong:
```
[2024-02-04 08:54:47,140] INFO in webapp: Received a POST request for adding a new item to the monitoring table with following data: {"appname": "testikene"}
[2024-02-04 08:54:47,143] ERROR in webapp: Encountered an error while inserting the new item: 
[2024-02-04 08:54:47,144] ERROR in webapp: duplicate key value violates unique constraint "monitoring_pkey"
DETAIL:  Key (appname)=(testikene) already exists.
[2024-02-04 08:54:47,144] ERROR in webapp: Encountered an error while adding new application testikene to monitoring table
```
### List all items in webapp database
Following API endpoint can be used for listing all items that exist in webapp database:
```
http://<webapp_domain>:<webapp_port>/list-items
```
Listing items via CLI:
```
teele@sk-demo:~$ curl http://webapp.demo:8080/list-items
[{"ID":"1","appname":"nginx","status":"OK"},{"ID":"2","appname":"testikene","status":"OK"},{"ID":"4","appname":"anotheritem","status":"OK"}]
```
Listing items via browser:

![alt text](list_items.PNG)
### List details about a specific item in webapp database
Following API endpoint can be used for listing details about a specific item in webapp database:
```
http://<webapp_domain>:<webapp_port>/list-item/<appname>
```
Listing details about app **testikene** via CLI:
```
teele@sk-demo:~/repo/demo-webapp$ curl http://webapp.demo:8080/list-item/testikene
{"ID":"2","appname":"testikene","status":"OK"}
```
Listing details about app **testikene** via browser:

![alt text](list_specific_item.PNG)
### Get status of a specific item in webapp database
Following API endpoint dan be used for requesting status of the specified item:
```
http://<webapp_domain>:<webapp_port>/get-status/<appname>
```
Requesting the status of application **testikene** via CLI:
```
teele@sk-demo:~/repo/demo-webapp$ curl http://webapp.demo:8080/get-status/testikene
{"status":"OK"}
```
Requesting the status of application **testikene** via browser:

![alt text](get_status.PNG)

### Update the status of a specific item in webapp database
Following API endpoint can be used for updating the value of column **status** for the specified item in webapp database via HTTP POST request:
```
http://<webapp_domain>:<webapp_port>/update-status
```
The logic of status updating was written to be compatible with Grafana alerting via webhook (more details about Grafana alert json body structure can be found from https://prometheus.io/docs/alerting/latest/configuration/#webhook_config). This means that the HTTP POST requests sent to this endpoint should follow some rules:
  - json body should have key **alerts** which is a list of dictionaries
  - dictionaries in **alerts** list should contain following information:
    -  key **status** (string) ---> to change the item status in database to PROBLEM, set the value of **status** key to "firing". To change the item status in database to OK, set the value of **status** key to "resolved". If some other value is specified, then API will skip this item.
    - key **labels** (dictionary) ---> **labels** value needs to be a dictionary that contains key **appname**. Value of **appname** key should match with the application's name in webapp database as this value is used during the SQL UPDATE query for identifying the correct application
- example payload for changing the status of application **testikene** to PROBLEM:
  ```
   {"alerts": [{"status": "firing", "labels": {"appname": "testikene"}}]}
  ``` 
API will respond with a list of dictionaries to let the user know if the updates to specified applications were successful.

Sending a HTTP POST request via CLI to change status of **testikene** to PROBLEM:
```
teele@sk-demo:~/repo/demo-webapp/ansible$ curl -X POST http://webapp.demo:8080/update-status -H 'Content-Type: application/json' -d '{"alerts": [{"status": "firing", "labels": {"appname": "testikene"}}]}'
[{"appname":"testikene","update":"success"}]   
``` 
Checking the status of **testikene** after updating the status:
```
teele@sk-demo:~/repo/demo-webapp/ansible$ curl http://webapp.demo:8080/get-status/testikene
{"status":"PROBLEM"} 
``` 
Changing the status of **testikene** back to OK and checking the results:
```
teele@sk-demo:~/repo/demo-webapp/ansible$ curl -X POST http://webapp.demo:8080/update-status -H 'Content-Type: application/json' -d '{"alerts": [{"status": "resolved", "labels": {"appname": "testikene"}}]}'
[{"appname":"testikene","update":"success"}]
teele@sk-demo:~/repo/demo-webapp/ansible$ curl http://webapp.demo:8080/get-status/testikene
{"status":"OK"}
``` 

## Testing webapp locally with provided demo resources