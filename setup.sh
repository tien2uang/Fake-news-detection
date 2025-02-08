


#Setup training topic
kafka-console-consumer --topic training_data --bootstrap-server localhost:9092
kafka-console-producer --topic training_data --bootstrap-server localhost:9092
#Setup inferrence topic
kafka-console-consumer --topic inferrence_data --bootstrap-server localhost:9092
kafka-console-producer --topic inferrence_data --bootstrap-server localhost:9092







