FROM repo.walkingtree.tech/python:3.10.12

WORKDIR /app

COPY . /app

RUN apt-get update && apt-get install -y sudo swig libgl1-mesa-glx libreoffice  poppler-utils 


RUN python3 -m venv .venv

RUN /bin/bash -c "source .venv/bin/activate"

RUN pip install python-dotenv


RUN pip install  -r requirements.txt     

EXPOSE 8080
CMD ["python3", "run_server.py"]
