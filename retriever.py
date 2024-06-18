import os
import json
import models
import requests
from openai import OpenAI
from dotenv import load_dotenv
from constants import Constants
import prompts
import streamlit as st
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings

from llama_index.core import VectorStoreIndex, get_response_synthesizer
from llama_index.core import SimpleDirectoryReader
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.postprocessor import SimilarityPostprocessor


load_dotenv()

os.environ['OPENAI_API_KEY']=os.getenv("OPENAI_API_KEY")

def main():
    st.title("Retriever")

    # stores the file paths
    # file_paths:list[str] = models.upload_files()
    # text:str = models.from_paths_to_text(file_paths)

    file_paths:list[str] = ['data/reterival_data/planet-positive.pdf',
                            'data/reterival_data/Untitled spreadsheet.xlsx']
    
    data_model = {
  "id": "A unique identifier for the document or item, if not present provide null.",
  "specVersion": "The version of the specification that this document adheres to, if not present provide null.",
  "version": "A numeric version of this document or item, if not present provide null.",
  "created": "A timestamp indicating when the document or item was created, if not present provide null.",
  "status": "The current status of the document or item (e.g., active, inactive, draft), if not present provide null.",
  "validityPeriodStart": "The start date of the period during which the document or item is valid, if not present provide null.",
  "validityPeriodEnd": "The end date of the period during which the document or item is valid, if not present provide null.",
  "companyName": "The name of the company associated with the document or item, if not present provide null.",
  "companyIds": [
    "An identifier for the company, if not present provide null."
  ],
  "productDescription": "A description of the product, if not present provide null.",
  "productIds": [
    "An identifier for the product, if not present provide null."
  ],
  "productCategoryCpc": "The category code for the product (e.g., CPC code), if not present provide null.",
  "productNameCompany": "The product name as given by the company, if not present provide null.",
  "pcf": {
    "declaredUnit": "The unit in which the product's environmental data is declared, if not present provide null.",
    "unitaryProductAmount": "The amount of the product in the declared unit, if not present provide null.",
    "pCfExcludingBiogenic": "The product carbon footprint excluding biogenic emissions, if not present provide null.",
    "pCfIncludingBiogenic": "The product carbon footprint including biogenic emissions, if not present provide null.",
    "fossilGhgEmissions": "The amount of fossil greenhouse gas emissions, if not present provide null.",
    "fossilCarbonContent": "The amount of fossil carbon content, if not present provide null.",
    "biogenicCarbonContent": "The amount of biogenic carbon content, if not present provide null.",
    "dLucGhgEmissions": "The amount of direct land use change greenhouse gas emissions, if not present provide null.",
    "landManagementGhgEmissions": "The amount of greenhouse gas emissions from land management, if not present provide null.",
    "otherBiogenicGhgEmissions": "The amount of other biogenic greenhouse gas emissions, if not present provide null.",
    "iLucGhgEmissions": "The amount of indirect land use change greenhouse gas emissions, if not present provide null.",
    "biogenicCarbonWithdrawal": "The amount of biogenic carbon withdrawal, if not present provide null.",
    "aircraftGhgEmissions": "The amount of greenhouse gas emissions from aircraft, if not present provide null.",
    "characterizationFactors": "Characterization factors used in the assessment, if not present provide null.",
    "ipccCharacterizationFactorsSources": [
      "Sources of IPCC characterization factors, if not present provide null."
    ],
    "crossSectoralStandardsUsed": [
      "Cross-sectoral standards used in the assessment, if not present provide null."
    ],
    "productOrSectorSpecificRules": [
      {
        "operator": "The type of operator (e.g., manufacturer, supplier), if not present provide null.",
        "ruleNames": [
          "Names of the rules applicable to the product or sector, if not present provide null."
        ],
        "otherOperatorName": "The name of the operator if not categorized, if not present provide null."
      }
    ],
    "biogenicAccountingMethodology": "The methodology used for biogenic accounting, if not present provide null.",
    "boundaryProcessesDescription": "Description of the boundary processes considered, if not present provide null.",
    "referencePeriodStart": "The start date of the reference period, if not present provide null.",
    "referencePeriodEnd": "The end date of the reference period, if not present provide null.",
    "geographicScope": {
      "geographyRegionOrSubregion": "The geographic region or subregion covered, if not present provide null."
    },
    "secondaryEmissionFactorSources": [
      {
        "name": "The name of the secondary emission factor source, if not present provide null.",
        "version": "The version of the secondary emission factor source, if not present provide null."
      }
    ],
    "exemptedEmissionsPercent": "The percentage of emissions that are exempted, if not present provide null.",
    "exemptedEmissionsDescription": "Description of the exempted emissions, if not present provide null.",
    "packagingEmissionsIncluded": "Indicates if packaging emissions are included (true/false), if not present provide null.",
    "allocationRulesDescription": "Description of the allocation rules applied, if not present provide null.",
    "uncertaintyAssessmentDescription": "Description of the uncertainty assessment, if not present provide null.",
    "primaryDataShare": "The percentage of primary data used, if not present provide null.",
    "dqi": {
      "coveragePercent": "The percentage of coverage in the data quality indicator, if not present provide null.",
      "technologicalDQR": "The rating for technological data quality, if not present provide null.",
      "temporalDQR": "The rating for temporal data quality, if not present provide null.",
      "geographicalDQR": "The rating for geographical data quality, if not present provide null.",
      "completenessDQR": "The rating for completeness data quality, if not present provide null.",
      "reliabilityDQR": "The rating for reliability data quality, if not present provide null."
    },
    "assurance": {
      "assured": "Indicates if the data is assured (true/false), if not present provide null.",
      "providerName": "The name of the assurance provider, if not present provide null."
    }
  }
}

    
    product_names = list(models.find_product_from_documents(file_paths, data_model))
    st.write(product_names)

    documents = SimpleDirectoryReader("data/reterival_data").load_data()

    # build index
    index = VectorStoreIndex.from_documents(documents)

    # configure retriever
    retriever = VectorIndexRetriever(
        index=index,
        similarity_top_k=5,
    )

    # configure response synthesizer
    response_synthesizer = get_response_synthesizer()

    # assemble query engine
    query_engine = RetrieverQueryEngine(
        retriever=retriever,
        response_synthesizer=response_synthesizer,
        node_postprocessors=[SimilarityPostprocessor(similarity_cutoff=0.7)],
    )

    # query
    json_objects: list[dict] = []
    for id, product_name in enumerate(product_names):
        response = query_engine.query(product_name)
        # print(response)
        st.write(product_name)
        doc = ""
        for idx, node in enumerate(response.source_nodes):
            doc += f"Document {idx+1}\n"
            doc += node.text
            doc += f'\n\n {"="*50}'
        messages = [{'role': 'system', 'content': 'You are a helpful assistant and give respone only as json. You have the capability to understand the context of the given data and provide the response accordingly.'},
                    {'role': 'user', 'content': f'''
                     Our main goal is to create a JSON object detailing various product-related information. You are provided with the company's environmental data, such as energy consumption, carbon emissions, and more, along with the product name and a data model. Follow these steps:

                      1. Understand the provided data:
                        - Product name: {product_name}
                        - Documents: {doc}
                        - Data model: {data_model}

                      2. Based on the provided data and product name, create a similar data model that stores all the carbon footprint data of the product.

                      3. If any field's values are missing in the document, assign its value as null. Do not make up its values or remove fields.

                      4. Provide the response strictly in JSON format.
        '''}]
        data_model = models.call_gpt(messages, temperature=0)['data'].content.strip()
        data_model = data_model.split("```")[1].split("json")[-1].strip()
        print(f"{id+1}th Data Model successfully created.")
        json_objects.append(json.loads(data_model))
    st.write(json_objects)
    file_name = "data/data_model/data_model.json"

    # Open a file in write mode
    with open(file_name, 'w') as json_file:
        # Write the JSON data to the file
        json.dump(json_objects, json_file, indent=4)


if __name__ == "__main__":
    main()