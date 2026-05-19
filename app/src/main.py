import uvicorn

from fastapi import FastAPI


app = FastAPI(
    title="FoodTrack API",
    description="Cross-platform mobile app for automated food expiration tracking",
    version="1.0.0",
    docs_url='/api/openapi',
    openapi_url='/api/openapi.json',
)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
