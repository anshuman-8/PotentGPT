# Search Probe
### Probe 1.5

### Features
- Search capabilities by accessing data from Google, Bing, Google local business.
- Returns contact details in a well structured output.
- Helps you find the right person to help you with your goals.

### Running
1. Ensure Docker is installed and running on your system.
2. Clone the repository
3. Rename `sample.config.toml` to `config.toml` and flling all the fields in the file.
5. Ensure you are in the directory containing the `docker-compose.yaml` file and execute:

   ```bash
   docker compose up -d
   ```
   
### Development
```bash
# Run
uvicorn main:app --reload
```


