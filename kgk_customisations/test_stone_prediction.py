"""
Test script to check Stone Prediction data
Run with: bench --site [sitename] execute kgk_customisations.test_stone_prediction
"""

import frappe

def test_data():
    """Check if there's data in Stone Prediction"""
    
    # Get count
    count = frappe.db.count("Stone Prediction")
    print(f"\nTotal Stone Predictions: {count}")
    
    if count > 0:
        # Get sample records
        records = frappe.db.get_all(
            "Stone Prediction",
            fields=["name", "predicted_number_of_cuts", "parcel_name", "prediction_date"],
            limit=5
        )
        
        print("\nSample records:")
        for rec in records:
            print(f"  - Name: {rec.name}")
            print(f"    Lot ID (predicted_number_of_cuts): '{rec.predicted_number_of_cuts}' (type: {type(rec.predicted_number_of_cuts).__name__})")
            print(f"    Serial Number (parcel_name): '{rec.parcel_name}' (type: {type(rec.parcel_name).__name__})")
            print(f"    Date: {rec.prediction_date}")
            print()
    else:
        print("\nNo Stone Prediction records found!")

if __name__ == "__main__":
    test_data()
