# RAG sur plusieurs fichiers (Notes)
import os
from mcp import types
from mistralai.client import Mistral
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
import json
import pickle
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

#initialisation de l'API Key pour MistralAI
nextcloud_dir = os.getenv("NEXTCLOUD")
api_key_path = os.path.join(nextcloud_dir, "ConfigPerso", "api_key.json")
conf_file = json.load(open(api_key_path))
MISTRAL_API_KEY = conf_file["API_KEY_Mistal"]
client = Mistral(api_key=MISTRAL_API_KEY)
path_embedding_db = os.path.join(nextcloud_dir, "Data", "Notes_embedding_db.pkl")

def list_files_in_directory(directory):
    print(f"Contenu du répertoire {directory} :")
    list_paths = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            print(os.path.join(root, file))
            list_paths.append(os.path.join(root, file))
    if not list_paths:
        print("Aucun fichier trouvé")
    return list_paths


def create_doc_segments():
    files = list_files_in_directory(os.path.join(nextcloud_dir, "Notes"))

    text_segment_size = 200
    overlap_size = 40
    all_documents = []


    # --- 1. Boucle de traitement des fichiers ---
    for path in files:
        if not os.path.exists(path):
            print(f"Fichier introuvable : {path}")
            continue
            
        print(f"Traitement de: {os.path.basename(path)}")
        with open(path, 'r', encoding='utf-8') as f:
            doc = f.read()

            # --- 2. Découpage intelligent ---
            # On utilise RecursiveCharacterTextSplitter au lieu d'un while manuel
            # car il respecte la structure des phrases et paragraphes.
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=text_segment_size,
                chunk_overlap=overlap_size,
                separators=["\n\n", "\n", ".", "#","-"]
            )

            #if any(word in doc for word in banned_keywords):
            #        continue

            # On découpe le texte de CETTE page uniquement
            page_chunks = splitter.split_text(doc)
            
            for chunk in page_chunks:
                all_documents.append(
                    Document(
                        page_content=chunk, 
                        metadata={
                            "source": os.path.basename(path), 
                        }
                    )
                )
            
    print(f"\nTotal de segments créés : {len(all_documents)}")
    return all_documents   

    
def create_and_save_db(all_documents, db_path, batch_size=50):
    print(f"Calcul des embeddings pour {len(all_documents)} segments...")
    
    texts = [doc.page_content for doc in all_documents]
    metadatas = [doc.metadata for doc in all_documents]
    
    all_vectors = []
    
    # On découpe en lots pour ne pas dépasser la limite de l'API
    for i in range(0, len(texts), batch_size):
        batch_texts = texts[i : i + batch_size]
        print(f"Envoi du lot {i//batch_size + 1} ({len(batch_texts)} segments)...")
        
        try:
            embeddings_response = client.embeddings.create(
                model="mistral-embed",
                inputs=batch_texts,
            )
            # On extrait les vecteurs de ce lot
            batch_vectors = [data.embedding for data in embeddings_response.data]
            all_vectors.extend(batch_vectors)
        except Exception as e:
            print(f"Erreur lors du lot {i}: {e}")
            break

    # On vérifie qu'on a bien tout récupéré avant de sauver
    if len(all_vectors) == len(texts):
        data_to_save = {
            "vectors": all_vectors,
            "texts": texts,
            "metadatas": metadatas
        }
        
        with open(db_path, "wb") as f:
            pickle.dump(data_to_save, f)
        print(f"Succès ! Base sauvegardée ({len(all_vectors)} vecteurs).")
    else:
        print("Erreur : Le nombre de vecteurs ne correspond pas au nombre de textes.")



def query_custom_db(client, query, db_path, k=3):
    # 1. Charger la base
    with open(db_path, "rb") as f:
        db = pickle.load(f)
    
    # 2. Convertir la question en vecteur via Mistral
    query_resp = client.embeddings.create(
        model="mistral-embed",
        inputs=[query],
    )
    query_vector = np.array(query_resp.data[0].embedding).reshape(1, -1)
    
    # 3. Calculer la similarité (Maths pures)
    stored_vectors = np.array(db["vectors"])
    similarities = cosine_similarity(query_vector, stored_vectors)[0]
    
    # 4. Récupérer les K meilleurs indices
    best_indices = np.argsort(similarities)[::-1][:k]
    
    print(f"\n--- Résultats pour : {query} ---")
    text_results = ""
    for idx in best_indices:
        score = similarities[idx]
        source = db["metadatas"][idx].get("source", "Inconnu")
        content = db["texts"][idx]
        print(f"Score: {score:.4f} | Source: {source} \nContent: {content[:200]}...\n")
        text_results += f"Source: {source} | Score: {score:.4f}\n{content}\n---\n"
    
    return text_results


async def call_rag_notes_tool(name: str, arguments: dict) -> list[types.TextContent]:
    if name != "rag_notes_search":
        raise ValueError(f"Unknown tool: {name}")

    params = {"query": arguments["query"], "nb_k": arguments.get("k", ""), "refresh_db": arguments.get("refresh_db", False)}
    all_segments= create_doc_segments()
    create_and_save_db(all_segments, path_embedding_db)
    list_results = query_custom_db(client, "Quels sont mes projets en cours ?", db_path=path_embedding_db, k=3)
    
    return [types.TextContent(type="text", text=list_results)]


async def list_rag_notes_tool() -> list[types.Tool]:
    return [
        types.Tool(
            name="rag_notes_search",
            description="Recherche d'informations dans mes notes personnelles",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "la requete de recheche , quels sont les achats à faire"},
                    "k": {"type": "string", "description": "le nombre de résultat à retourner"},
                    "refresh_db": {"type": "boolean", "description": "si true , la base d'embeddings sera recréée à partir des fichiers actuels"}
                },
                "required": ["query"],
            },
        )
    ]
