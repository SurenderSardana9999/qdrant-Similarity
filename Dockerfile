# Use an official Python 3.11.5 runtime as the base image
FROM python:3.11.5-bookworm

# Install system dependencies
 RUN apt-get update && apt-get install -y libgl1-mesa-glx
 RUN apt-get update && apt-get install -y  libmariadbd-dev

# Set the working directory inside the container
 WORKDIR /ADA

# Copy the requirements file into the container
 COPY requirements.txt .

# Install the Python dependencies
 RUN pip3.11 install --no-cache-dir --upgrade pip
 RUN pip3.11 install --no-cache-dir -r requirements.txt

 COPY . .

 EXPOSE 8001

 CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]