CISC 886 – Cloud Computing
Project: Cloud-based Conversational Chatbot
Initial documentation

In this project, you will design and deploy a cloud-based conversational chatbot by fine-tuning a lightweight Large Language Model (LLM) on a large dataset using distributed computing on AWS. This project integrates key cloud computing concepts including storage virtualization, compute scaling, big data processing with Apache Spark, and cloud deployment. The aim of the project is to give you a hands-on experience with a real-world end-to-end ML pipeline on the cloud.

Requirements:

Select Your Base LLM: your need to select a small but capable open-source base models. You may use e.g., Use TinyLlama-1.1B or other similar model for your experiment. Download your chosen model from HuggingFace Hub and upload it to your S3 bucket.

Each group will use a different domain dataset (all 20M+ records) so their chatbot specializes in a different area. For example, you can select for General Conversational Chatbot, Healthcare & Medical Chatbot, Legal Assistant Chatbot, Tech Support Chatbot, etc.

Uploading the selected dataset to your Amazon S3 bucket in a structured folder

Youn need to perform Data Processing with Apache Spark on AWS EMR

You need to Fine-Tune the LLM

Deploying and testing the Chatbot Using AWS
