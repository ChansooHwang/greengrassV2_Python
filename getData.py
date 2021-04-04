import asyncio
import logging
import random
import time
from pytz import timezone
from datetime import datetime

import sys
import json

# import pymodbus libraries for the modbus client
from pymodbus.client.sync import ModbusTcpClient as ModbusClient
from pymodbus.payload import BinaryPayloadDecoder
from pymodbus.constants import Endian
from pymodbus.compat import iteritems
from collections import OrderedDict

# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os

from awscrt.io import (
    ClientBootstrap,
    DefaultHostResolver,
    EventLoopGroup,
    SocketDomain,
    SocketOptions,
)
from awsiot.eventstreamrpc import Connection, LifecycleHandler, MessageAmendment
import awsiot.greengrasscoreipc.client as client
from awsiot.greengrasscoreipc.model import PublishToIoTCoreRequest, QOS

TIMEOUT = 10


class IPCUtils:
    def connect(self):
        elg = EventLoopGroup()
        resolver = DefaultHostResolver(elg)
        bootstrap = ClientBootstrap(elg, resolver)
        socket_options = SocketOptions()
        socket_options.domain = SocketDomain.Local
        amender = MessageAmendment.create_static_authtoken_amender(os.getenv("SVCUID"))
        hostname = os.getenv("AWS_GG_NUCLEUS_DOMAIN_SOCKET_FILEPATH_FOR_COMPONENT")
        connection = Connection(
            host_name=hostname,
            port=8033,
            bootstrap=bootstrap,
            socket_options=socket_options,
            connect_message_amender=amender,
        )
        self.lifecycle_handler = LifecycleHandler()
        connect_future = connection.connect(self.lifecycle_handler)
        connect_future.result(TIMEOUT)
        return connection

ipc_utils = IPCUtils()
connection = ipc_utils.connect()
ipc_client = client.GreengrassCoreIPCClient(connection)

logger = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stdout, level=logging.INFO)

logger.info("Start Program")

def solar_modbus_data(address, name, databit, datatype):
    count = (int)(databit/16)
    return_value = {}
    try:
        mbclient.connect()
        # set the address and number of bytes that will be read on the modbus device
        # read the input register value 
        rr = mbclient.read_holding_registers(address, count, unit=1)
        # print(rr.__dict__)
        decoder = BinaryPayloadDecoder.fromRegisters(rr.registers, byteorder=Endian.Big, wordorder=Endian.Little)
        decode_list = []
        if databit == 16:
            if datatype == 'int':
                decode_list.append((name, decoder.decode_16bit_int()))
            else:
                decode_list.append((name, decoder.decode_16bit_uint()))
        else:
            if datatype == 'int':
                decode_list.append((name, decoder.decode_32bit_int()))
            elif datatype == 'uint':
                decode_list.append((name, decoder.decode_32bit_uint()))
            else:
                decode_list.append((name, decoder.decode_32bit_float()))
                
        decoded = OrderedDict(decode_list)

        for name, value in iteritems(decoded):
            return_value[name] = round(value, 1)

    except Exception as e:
        logging.info("Error: {0}".format(str(e)))
        return_value = {}

    return return_value
 
def publishMessage_mqtt(mqtt_topic, payload):
    try:
        
        message = json.dumps(payload)
        qos = QOS.AT_LEAST_ONCE

        request = PublishToIoTCoreRequest()
        request.topic_name = mqtt_topic
        request.payload = bytes(message, "utf-8")
        request.qos = qos
        operation = ipc_client.new_publish_to_iot_core()
        operation.activate(request)
        future = operation.get_response()
        future.result(TIMEOUT)

    except Exception as e:
        logging.info("Publish MQTT Message Error : {0}, topic : {1}, payload : {2}".format(str(e), mqtt_topic, message))


def main():
      
    logger.info("{0} - Start Publishing MQTT message".format(datetime.now(timezone('Asia/Seoul')).strftime('%Y%m%d%H%M%S')))
    oldSec = datetime.now(timezone('Asia/Seoul')).strftime('%S')

    while True:
        try:
            newSec = datetime.now(timezone('Asia/Seoul')).strftime('%S')
            if newSec != oldSec:
                dic_data = {}

                dic_data["time_stamp"] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                dic_data["timestamp_kst"] = datetime.now(timezone('Asia/Seoul')).strftime('%Y-%m-%d %H:%M:%S')
                dic_data["company"] = company
                dic_data["plant"] = plant
                dic_data["LINE1"] = {}
                dic_data["LINE2"] = {}

                # PV1 발전량
                pv1_solar_power = solar_modbus_data(37001, 'solar_power', 32, 'float')
                dic_data["LINE1"].update(pv1_solar_power)
                # PV1 누적발전량
                pv1_acc_solar_power = solar_modbus_data(37023, 'acc_solar_power', 32, 'float')
                dic_data["LINE1"].update(pv1_acc_solar_power)


                # PV2 발전량
                pv2_solar_power = solar_modbus_data(37031, 'solar_power', 32, 'float')
                dic_data["LINE2"].update(pv2_solar_power)
                # PV2 누적발전량
                pv2_acc_solar_power = solar_modbus_data(37053, 'acc_solar_power', 32, 'float')
                dic_data["LINE2"].update(pv2_acc_solar_power)

                # Battery Room Temp
                temp1 = solar_modbus_data(38000, 'temp1', 32, 'float')
                dic_data.update(temp1)

                # Battery Room Humidity
                hum1 = solar_modbus_data(38002, 'hum1', 32, 'float')
                dic_data.update(hum1)

                # 합계
                solar_power = pv1_solar_power['solar_power'] + pv2_solar_power['solar_power']
                dic_data["solar_power"] = solar_power

                # print(dic_data)
                publishMessage_mqtt(topic_header, dic_data)

                # Publish 후 publish한 시간을 oldSec으로 저장
                oldSec = newSec
            
            time.sleep(0.1)

        except asyncio.TimeoutError:
            logger.info("{0} - Timed out while executing".format(datetime.now(timezone('Asia/Seoul')).strftime('%Y%m%d%H%M%S')))
        except Exception as e:
            logger.info("Exception while running : " + repr(e))
    

if __name__ == "__main__":
    global mbclient, topic_header, company, plant, p_ip, p_port
    print("Start Program with parameters(IP, Port, Company, Plant) : ", sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
    p_ip = sys.argv[1]
    p_port = sys.argv[2]
    p_company = sys.argv[3]
    p_plant = sys.argv[4]

    mbclient = ModbusClient(p_ip, port=p_port)
    topic_header = 'rt/'+p_company+'/'+p_plant
    company = p_company.upper()
    plant = p_plant.upper()
    print('mqtt : ' + topic_header)
    main()