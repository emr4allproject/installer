#!/bin/bash

# Update package list
echo "Updating package list..."
sudo apt-get update

# Check system time settings
echo "Checking system time settings..."
timedatectl

# Edit APT sources (Backup existing sources.list)
echo "Editing APT sources list..."
sudo cp /etc/apt/sources.list /etc/apt/sources.list.bak
echo "/bookworm-security main contrib non-free non-free-firmware" | sudo tee -a /etc/apt/sources.list
echo "/sid main" | sudo tee -a /etc/apt/sources.list
sudo apt update

# Install Java 8
echo "Installing Java 8..."
sudo apt-get install -y openjdk-8-jdk
java -version

# Create Tomcat group and user
echo "Setting up Tomcat..."
sudo groupadd tomcat
sudo useradd -s /bin/false -g tomcat -d /opt/tomcat tomcat

# Download and extract Tomcat
wget https://dlcdn.apache.org/tomcat/tomcat-9/v9.0.86/bin/apache-tomcat-9.0.86.tar.gz
sudo mkdir /opt/tomcat
sudo tar -xzf apache-tomcat-9.0.86.tar.gz -C /opt/tomcat --strip-components=1
sudo chown -R tomcat:tomcat /opt/tomcat

# Configure Tomcat as a service
echo "Configuring Tomcat as a service..."
sudo bash -c 'cat > /etc/systemd/system/tomcat.service << EOF
[Unit]
Description=Apache Tomcat Web Application Container
After=network.target

[Service]
Type=forking
User=tomcat
Group=tomcat
UMask=0007
Environment=JAVA_HOME=/usr/lib/jvm/java-1.8.0-openjdk-amd64
Environment=CATALINA_PID=/opt/tomcat/temp/tomcat.pid
Environment=CATALINA_HOME=/opt/tomcat
Environment=CATALINA_BASE=/opt/tomcat
Environment='CATALINA_OPTS=-Xms512M -Xmx1024M -server -XX:+UseParallelGC'
ExecStart=/opt/tomcat/bin/startup.sh
ExecStop=/opt/tomcat/bin/shutdown.sh
RestartSec=10
Restart=always

[Install]
WantedBy=multi-user.target
EOF'

sudo systemctl daemon-reload
sudo systemctl start tomcat
sudo systemctl enable tomcat.service
sudo systemctl status tomcat

# Set root password
echo "Setting root password..."
echo "Please set the root password:"
sudo passwd root

# Configure Tomcat users
echo "Configuring Tomcat users..."
sudo bash -c 'cat > /opt/tomcat/conf/tomcat-users.xml << EOF
<role rolename="tomcat"/>
<role rolename="admin"/>
<role rolename="manager"/>
<role rolename="manager-gui"/>
<user username="admin" password="admin" roles="tomcat,admin,manager,manager-gui"/>
EOF'

# Install MySQL
echo "Installing MySQL..."
sudo apt install -y mysql-server
sudo apt-get install -y libaio1 libncurses5 libnuma-dev
sudo systemctl status mysql

# Configure MySQL
echo "Configuring MySQL..."
sudo mysql << EOF
ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY 'root1234';
exit;
EOF
sudo mysql_secure_installation

# Download and deploy OpenMRS
echo "Downloading and deploying OpenMRS..."
mkdir /var/lib/OpenMRS
sudo chown -R tomcat:tomcat /var/lib/OpenMRS
cd /home/pi/downloads
wget https://sourceforge.net/projects/openmrs/files/releases/OpenMRS.war
sudo cp OpenMRS.war /opt/tomcat/webapps/

echo "Installation complete! Open your browser and navigate to http://localhost:8080/openmrs to complete the setup."
#!/bin/bash

# Exit on errors
set -e

# 1. System Update and Preparation
echo "Updating package list and system..."
sudo apt-get update
sudo apt-get upgrade -y

echo "Checking system time settings..."
timedatectl

echo "Editing APT sources list..."
sudo bash -c 'cat <<EOF >> /etc/apt/sources.list
deb http://deb.debian.org/debian bookworm-security main contrib non-free non-free-firmware
deb http://deb.debian.org/debian sid main
EOF'
sudo apt-get update

# 2. Install Java 8
echo "Installing Java 8..."
sudo apt-get install -y openjdk-8-jdk
java -version

# 3. Install and Configure Tomcat
echo "Setting up Tomcat..."
sudo groupadd tomcat || true
sudo useradd -s /bin/false -g tomcat -d /opt/tomcat tomcat || true

echo "Downloading Tomcat..."
wget https://dlcdn.apache.org/tomcat/tomcat-9/v9.0.86/bin/apache-tomcat-9.0.86.tar.gz -P /tmp
sudo mkdir -p /opt/tomcat
sudo tar -xzf /tmp/apache-tomcat-9.0.86.tar.gz -C /opt/tomcat --strip-components=1
sudo chown -R tomcat:tomcat /opt/tomcat

echo "Configuring Tomcat service..."
sudo bash -c 'cat <<EOF > /etc/systemd/system/tomcat.service
[Unit]
Description=Apache Tomcat Web Application Container
After=network.target
[Service]
Type=forking
User=tomcat
Group=tomcat
UMask=0007
Environment=JAVA_HOME=/usr/lib/jvm/java-1.8.0-openjdk-amd64
Environment=CATALINA_PID=/opt/tomcat/temp/tomcat.pid
Environment=CATALINA_HOME=/opt/tomcat
Environment=CATALINA_BASE=/opt/tomcat
Environment="CATALINA_OPTS=-Xms512M -Xmx1024M -server -XX:+UseParallelGC"
ExecStart=/opt/tomcat/bin/startup.sh
ExecStop=/opt/tomcat/bin/shutdown.sh
RestartSec=10
Restart=always
[Install]
WantedBy=multi-user.target
EOF'

sudo systemctl daemon-reload
sudo systemctl start tomcat
sudo systemctl enable tomcat.service

# Configure Tomcat users
echo "Configuring Tomcat users..."
sudo bash -c 'cat <<EOF > /opt/tomcat/conf/tomcat-users.xml
<tomcat-users>
  <role rolename="tomcat"/>
  <role rolename="admin"/>
  <role rolename="manager"/>
  <role rolename="manager-gui"/>
  <user username="admin" password="admin" roles="tomcat,admin,manager,manager-gui"/>
</tomcat-users>
EOF'

# Modify Tomcat context.xml
sudo bash -c 'cat <<EOF > /opt/tomcat/webapps/docs/META-INF/context.xml
<Context antiResourceLocking="false" privileged="true"></Context>
EOF'

sudo bash -c 'cat <<EOF > /opt/tomcat/webapps/examples/META-INF/context.xml
<Context antiResourceLocking="false" privileged="true"></Context>
EOF'

# 4. Install MySQL
echo "Installing MySQL..."
sudo groupadd mysql || true
sudo useradd -g mysql mysql || true
sudo apt-get install -y mysql-server libaio1 libncurses5 libnuma-dev

echo "Securing MySQL installation..."
sudo mysql_secure_installation

echo "Configuring MySQL root user..."
sudo mysql -e "ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY 'root1234';"

# 5. Install OpenMRS
echo "Setting up OpenMRS..."
sudo mkdir -p /var/lib/OpenMRS
sudo chown -R tomcat:tomcat /var/lib/OpenMRS

echo "Downloading OpenMRS..."
wget https://sourceforge.net/projects/openmrs/files/releases/OpenMRS_2.12.2.war -P /tmp

echo "Deploying OpenMRS to Tomcat..."
sudo cp /tmp/OpenMRS_2.12.2.war /opt/tomcat/webapps/openmrs.war

# 6. Final Steps
echo "Installation completed. Please configure OpenMRS via your browser at http://localhost:8080/openmrs."
