import json
import os
from typing import Dict, List
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import redis
from rq import Connection, Queue
from rq.job import Job
from app.config import Configuration
from app.forms.classification_form import ClassificationForm
from app.ml.classification_utils import classify_image
from app.utils import list_images
import matplotlib.pyplot as plt


app = FastAPI()
config = Configuration()

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")


@app.get("/info")
def info() -> Dict[str, List[str]]:
    """Returns a dictionary with the list of models and
    the list of available image files."""
    list_of_images = list_images()
    list_of_models = Configuration.models
    data = {"models": list_of_models, "images": list_of_images}
    return data


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    """The home page of the service."""
    return templates.TemplateResponse("home.html", {"request": request})


@app.get("/classifications")
def create_classify(request: Request):
    return templates.TemplateResponse(
        "classification_select.html",
        {"request": request, "images": list_images(), "models": Configuration.models},
    )


@app.post("/classifications")
async def request_classification(request: Request):
    folder_path = "app/static/output/json/"
    # Check if the folder exists
    if not os.path.exists(folder_path):
        # If it doesn't exist, create it
        os.makedirs(folder_path)
    form = ClassificationForm(request)
    await form.load_data()
    image_id = form.image_id
    model_id = form.model_id
    classification_scores = classify_image(model_id=model_id, img_id=image_id)
    out = json.dumps(classification_scores)
    with open("app/static/output/json/out.json", "w") as outfile:
        outfile.write(out)
    return templates.TemplateResponse(
        "classification_output.html",
        {
            "request": request,
            "image_id": image_id,
            "classification_scores": out,
        },
    )
# Download JSON file containing prediction output
@app.get("/outputJSON")
def output_json():
    return FileResponse(path="out.json", filename="out.json", media_type='text/json')


# Download Image file containing plot
@app.get("/outputPNG")
def output_png():
    folder_path = "app/static/output/png/"
    # Check if the folder exists
    if not os.path.exists(folder_path):
        # If it doesn't exist, create it
        os.makedirs(folder_path)
    with open("app/static/output/json/out.json") as json_file:
        data = json.load(json_file)
        x = [item[0] for item in data]
        y = [item[1] for item in data]
        plt.barh(x, y)
        # setting label of y-axis
        plt.ylabel("Y")
        # setting label of x-axis
        plt.xlabel("X")
        plt.title("Prediction")
        plt.savefig('app/static/output/png/img.png')
        plt.clf()
        return FileResponse(path="app/static/output/png/img.png", filename="img.png", media_type='image/png')