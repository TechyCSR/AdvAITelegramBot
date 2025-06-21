from modules.core.database import get_user_interaction_collection

if __name__ == "__main__":
    coll = get_user_interaction_collection()
    result = coll.delete_many({})
    print(f"Deleted {result.deleted_count} documents from user_interactions collection.") 