# base-image for python on any machine using a template variable,
# see more about dockerfile templates here: https://www.balena.io/docs/learn/develop/dockerfile/
FROM balenalib/raspberry-pi-python:2

# use `install_packages` if you need to install dependencies,
# for instance if you need git, just uncomment the line below.
# RUN install_packages git

# Set our working directory
WORKDIR /usr/src/app

# Copy requirements.txt first for better cache on later pushes
COPY ./requirements.txt requirements.txt

# pip install python deps from requirements.txt on the resin.io build server
RUN pip install -r requirements.txt

# This will copy all files in our root to the working  directory in the container
COPY . ./

# Install local package
RUN pip install -e ./pyicloud

# switch on systemd init system in container
ENV INITSYSTEM on

# Enable udevd so that plugged dynamic hardware devices show up in our container
ENV UDEV=1

# update version
ENV APP_VERSION v0.0.2

# main.py will run when container starts up on the device
CMD ["python","-u","src/main.py"]
