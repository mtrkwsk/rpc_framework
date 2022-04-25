# pwt_rpc_framework

🚧 *Under development* 🚧

This is the framework for event-driven architecture based on MQTT messages. It's main purpose is to serve as an interface between distributed *components* of IoT-like network.

It's being used in PhyWise physical layer verification framework developed in Gdansk University of Technology.

The main aim is to allow the developers to write simple and modular applications on a distributed IoT-like networks.

## Important

📣This published part is responsible only for the communication and does not include proprietary signal processing, RF sample streaming, hardware/software simulation and other things developed in PhyWise.

## Main framework functionalities

The main aim of the framework is to orchestrate and communicate with many *components* of the testing system. The *Component* is self-contained part of the system f.e. some sensor making measurement, radio receiver, wireless node with mechanical interface etc. Component is distributed and it's meant to communicate with the framework only - not directly with other components. The framework communicates with the components in a following way:

* Getting component's status and its internal state
* Sending *command* to the component with particular arguments
* Getting *measurements* from component
* Changing internal *parameters* of the component

## The component functionalities

Component is just an application with MQTT support in accorance with the API specification. In this case - it is a python script main.py with pwtComponent module.

There are a few features of the component: 
* Component connects to the MQTT broker and use it to communicate with the framework
* Component is a placeholder for *driver* modules that can be loaded (in runtime) to the component. *Driver* is the implementation of a particular component's function like: sensor data acquisition, hardware interaction etc.
* After *registering* the driver, its @api_command decorated methods are visible automatically in the framework
* Some of @api_commands can be run in a separate thread by using @threaded decorator
* Each driver is started in a separate process in python and managed by pwtComponent module
* PwtComponent enables the drivers to send measurements to the queue
* PwtComponent receiving *set_parameters* commands and dispatch them to the apprioriate driver

## Jupyter Notebook
The whole framework can be managed by pwtAPI module, for example in a jupyter notebook.

## How to use it
To use the framework please use docker-compose to run the containers with everything needed for a simple test. Docker compose runs the following containers:

* RabbitMQ configured as MQTT broker
* JupyterLab to run a simple orchestration scenario
* Component with exemplary driver: TestDriver

You can observe the component behaviour in docker-compose log or attaching to pwt_component docker.
