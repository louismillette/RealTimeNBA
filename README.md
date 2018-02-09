# RealTimeNBA
Calculate NBA statistics in real time

# Stack (tenative)
- mongo DB for the database, hosted on AWS RDS instance
- node.js for real time server + front end, AWS EBS EC2 type stucture
- python 3.6 data + analytics, pulling data in real time AWS Lambda
- python + mongo local set up to build model and collect data 

# Database Structure

## Local Model Dastabase
This database is for building the model.  It won't be hosted online, we'll build the model and collect the data locally to save (a lot of) money.
we'll use 4 tables to store our data:
### PBP
the Play by Play table stores every play made in every game.  Should be about 450,000 plays per year stored in here, or approximately 9 million entries of 30 years.
