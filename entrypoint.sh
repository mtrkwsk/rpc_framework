#!/bin/sh

cd pwt.component
sh -c './wait-for rabbitmq_pwt:15672'
sh -c './wait-for rabbitmq_pwt:1883'
sh -c './wait-for rabbitmq_pwt:5672'


python main.py --mqtt rabbitmq_pwt -c $COMPONENT_NAME
