# Choosing the base image
FROM python:3.10-slim

# Setting the working directory to /app
WORKDIR /app

# Copying the requirements.txt file to the /app directory
COPY ./requirements/requirements.txt /app/

# Installing dependencies
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copying all files from the backend directory to the /app directory in the container
COPY . /app/

# Environment variable for Django
ENV PYTHONUNBUFFERED=1

# Running the Django application
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]