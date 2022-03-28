#import logging
#logging.basicConfig(level=logging.DEBUG)
from confluent_kafka import Consumer, KafkaError
import json
import os
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from slack_blockkit.block_element import TextObject
from slack_sdk.models.basic_objects import JsonObject


slack_token = os.environ["SLACK_API_TOKEN"]
client = WebClient(token=slack_token)

settings = {
    'bootstrap.servers': os.environ["KAFKA_BROKERS"],
    'group.id': 'python_slack',
#    'plugin.library.paths': 'monitoring-interceptor',
    'default.topic.config': {'auto.offset.reset': 'smallest'},
    'security.protocol': os.environ['SECURITY_PROTOCOL'],
    'ssl.ca.location': os.environ['KAFKA_CA_CERT'],
    'sasl.mechanism': os.environ['SASL_MECHANISM'],
    'sasl.username': os.environ['SASL_USERNAME'],
    'sasl.password': os.environ['SASL_PASSWORD']
}

c = Consumer(settings)

c.subscribe([os.environ['KAFKA_TOPIC']])

try:
    while True:
        msg = c.poll(0.1)

        if msg is None:
            continue

        elif not msg.error():
            print('Received message: {0}'.format(msg.value()))

            if msg.value() is None:
                continue

            # Handle UTF
            try:
                data = msg.value().decode()
            except Exception:
                data = msg.value()
            
            # Try to parse the message as JSON
            try:
                app_msg = json.loads(data)
            except Exception:
                print('Could not parse JSON, will just use raw message contents')
                app_msg = data
            
                
            channel= os.environ["SLACK_CHANNEL"]
            text= app_msg['TEXT']

            # Send the message to Slack
            print('\nSending message "{}" to channel {}'.format(text, channel))

            #extract json as strings 
            micka = json.dumps(app_msg)
            #split by comma
            mylist = micka.split(",")
            #strip payload to get gps coordinates
            gps = str(mylist[4]).strip('"GPS_COORDINATES": "') + "," + str(mylist[5]).strip('"GPS_COORDINATES": ","}')
            #text layout for slack
            text_layout_slack = str(mylist[1]) + "\n" + str(mylist[2]) + "\n" + str(mylist[3])

            response = client.chat_postMessage(
                channel="#general",
              #  text= "message: " + app_msg['message'] + "\n" + "host: " + app_msg['host'] + "\n" + "timestamp: " + app_msg['@timestamp']
                blocks= [
		{
			"type": "section",
			"text": {
				"type": "mrkdwn",
				"text": text_layout_slack
			},
			"accessory": {
				"type": "button",
				"text": {
					"type": "plain_text",
					"text": "GPS coordinate",
                    "emoji": True
					
				},
				"value": "click_me_123",
				"url": "https://www.google.com/maps/place/{0}".format(gps),
				"action_id": "button-action"
			}
		}
	]
            )


        elif msg.error().code() == KafkaError._PARTITION_EOF:
            print('End of partition reached {}/{}'
                  .format(msg.topic(), msg.partition()))

        else:
            print('Error occured: {}'.format(msg.error()))

except Exception as e:
    print(e)

finally:
    c.close()
