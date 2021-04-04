# greengrassV2_Python

태양광 발전소의 PMS에서 Modbus tcp를 이용하여 데이터를 수집하고 이를 AWS IoT Core 에 MQTT 로 Publish 하는 소스

Greengrass V2용


# 아래는 실제 Greengrass 에서 배포시 사용되는 레시피


{
  "RecipeFormatVersion": "2020-01-25",
  "ComponentName": "getRealTimeSolarData_Namjeoni1",
  "ComponentVersion": "2.1.2",
  "ComponentType": "aws.greengrass.generic",
  "ComponentDescription": "get realtime solar data",
  "ComponentPublisher": "CS Hwang",
  "ComponentConfiguration": {
    "DefaultConfiguration": {
      "Modbus_IP": "10.1.1.1",
      "Modbus_Port": 502,
      "Company": "ttt",
      "Plant": "tttt1",
      "accessControl": {
        "aws.greengrass.ipc.mqttproxy": {
          "getRealTimeSolarData:pubsub:1": {
            "policyDescription": "Allows access to publish to all topics.",
            "operations": [
              "aws.greengrass#PublishToIoTCore"
            ],
            "resources": [
              "*"
            ]
          }
        }
      }
    }
  },
  "Manifests": [
    {
      "Platform": {
        "os": "linux"
      },
      "Name": "Linux",
      "Lifecycle": {
        "Run": "python3 {artifacts:path}/getRealTimeSolarData.py {configuration:/Modbus_IP} {configuration:/Modbus_Port} {configuration:/Company} {configuration:/Plant}"
      },
      "Artifacts": [
        {
          "Uri": "s3://s3-greengrass-artifact/gg_python/getData/2.1.2/getData.py",
          "Digest": "9H5l9cen3YXzKvPSJPW+zgSzp8aYUCQIefh4E62M8f4=",
          "Algorithm": "SHA-256",
          "Unarchive": "NONE",
          "Permission": {
            "Read": "OWNER",
            "Execute": "NONE"
          }
        }
      ]
    }
  ],
  "Lifecycle": {}
}

