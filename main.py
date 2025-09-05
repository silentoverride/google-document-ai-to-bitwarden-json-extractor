import json
import os
import argparse
from google.cloud import documentai

def process_document(
    project_id: str,
    location: str,
    processor_id: str,
    file_path: str,
    mime_type: str,
) -> dict:
    """
    Processes a document using the Document AI API.
    """
    client_options = {"api_endpoint": f"{location}-documentai.googleapis.com"}
    client = documentai.DocumentProcessorServiceClient(client_options=client_options)

    # The full resource name of the processor, e.g.:
    # `projects/{project_id}/locations/{location}/processors/{processor_id}`
    name = client.processor_path(project_id, location, processor_id)

    # Read the file into memory
    with open(file_path, "rb") as image:
        image_content = image.read()

    # Load Binary Data into Document AI RawDocument Structure
    raw_document = documentai.RawDocument(content=image_content, mime_type=mime_type)

    # Configure the process request
    request = documentai.ProcessRequest(name=name, raw_document=raw_document)

    # Use the client to process the document
    result = client.process_document(request=request)

    # Get the document object from the result
    document = result.document

    # Create a dictionary to store the extracted entities
    extracted_data = {}

    # For a full list of Document object attributes, please reference this page:
    # https://cloud.google.com/document-ai/docs/reference/rest/v1/Document
    for entity in document.entities:
        # Fields that have a normalized value will have that value extracted
        if entity.normalized_value:
            extracted_data[entity.type_] = entity.normalized_value.text
        else:
            extracted_data[entity.type_] = entity.mention_text

    return extracted_data

def map_data_to_bitwarden(extracted_data: dict):
    """
    Maps the extracted data to the Bitwarden template.
    """
    # Read the Bitwarden template
    with open("bitwarden_id_template.json", "r") as f:
        template = json.load(f)

    # This is a simple example of how the data could be mapped.
    # In a real application, you would need to carefully map the
    # extracted fields to the correct fields in the Bitwarden template.
    # The entity types from Document AI will depend on the processor you are using.
    # For example, a driver's license processor will have different entity types
    # than a passport processor.

    # For demonstration purposes, we will map the mock data to the template.
    if "name" in extracted_data:
        # Split the name into first and last names
        # This is a simple implementation and might not work for all names.
        parts = extracted_data["name"].split(" ")
        template["identity"]["firstName"] = parts[0]
        template["identity"]["lastName"] = parts[-1]
        template["name"] = extracted_data["name"] + " ID"

    if "dob" in extracted_data:
        # Find the field with the name "DOB" and update its value
        for field in template["fields"]:
            if field["name"] == "DOB":
                field["value"] = extracted_data["dob"]
                break

    if "address" in extracted_data:
        template["identity"]["address1"] = extracted_data["address"]

    # Save the populated template to import_bitwarden.json
    with open("import_bitwarden.json", "w") as f:
        json.dump(template, f, indent=4)

    print("Successfully mapped data and saved to import_bitwarden.json")


def main():
    """
    Main function to process a document and save the extracted data.
    """
    parser = argparse.ArgumentParser(description="Process a document with Google Document AI and format for Bitwarden.")
    parser.add_argument("--file-path", help="The path to the input document file.")
    parser.add_argument("--project-id", help="Your Google Cloud project ID.")
    parser.add_argument("--location", help="The Google Cloud location for the Document AI processor (e.g., 'us').")
    parser.add_argument("--processor-id", help="Your Document AI processor ID.")
    parser.add_argument("--mime-type", default="application/pdf", help="The mime type of the input file.")
    parser.add_argument("--credentials", help="The path to your Google Cloud service account credentials JSON file. If not provided, the script will use the GOOGLE_APPLICATION_CREDENTIALS environment variable.")
    args = parser.parse_args()

    if args.credentials:
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = args.credentials

    try:
        if args.file_path and args.project_id and args.location and args.processor_id:
            print("Processing document with Google Document AI...")
            extracted_data = process_document(
                project_id=args.project_id,
                location=args.location,
                processor_id=args.processor_id,
                file_path=args.file_path,
                mime_type=args.mime_type,
            )
        else:
            print("Using mock data because not all required arguments were provided.")
            extracted_data = {
                "name": "John Doe",
                "dob": "01/01/1990",
                "address": "123 Main St, Anytown, USA",
            }

        with open("export.json", "w") as f:
            json.dump(extracted_data, f, indent=4)
        print("Successfully created export.json")

        map_data_to_bitwarden(extracted_data)

    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    main()
