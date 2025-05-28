import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, roc_curve, roc_auc_score
from sklearn.impute import SimpleImputer
import json

# Load the dataset
def load_data(filepath):
    df = pd.read_csv(filepath)
    print(f"Dataset loaded with {df.shape[0]} rows and {df.shape[1]} columns")
    return df

# Exploratory Data Analysis
def explore_data(df):
    # Check for missing values
    missing_values = df.isnull().sum()
    missing_percent = (missing_values / len(df)) * 100
    
    # Basic statistics
    numerical_columns = df.select_dtypes(include=['int64', 'float64']).columns
    statistics = df[numerical_columns].describe()
    
    # Churn distribution
    churn_distribution = df['Churn'].value_counts(normalize=True) * 100
    
    # Correlation matrix
    correlation_matrix = df.select_dtypes(include=['int64', 'float64']).corr()
    
    eda_results = {
        "missing_values": missing_values.to_dict(),
        "missing_percent": missing_percent.to_dict(),
        "statistics": statistics.to_dict(),
        "churn_distribution": churn_distribution.to_dict(),
        "correlation_matrix": correlation_matrix.to_dict()
    }
    
    return eda_results

# Preprocess data
def preprocess_data(df):
    # Handle 'TotalCharges' column which might be string due to spaces
    if df['TotalCharges'].dtype == 'object':
        df['TotalCharges'] = pd.to_numeric(df['TotalCharges'], errors='coerce')
    
    # Drop customer ID column
    if 'customerID' in df.columns:
        df = df.drop('customerID', axis=1)
    
    # Convert binary categorical variables to numeric
    binary_vars = ['gender', 'Partner', 'Dependents', 'PhoneService', 'PaperlessBilling', 'Churn']
    for var in binary_vars:
        if var in df.columns:
            df[var] = df[var].map({'Yes': 1, 'No': 0, 'Male': 1, 'Female': 0})
    
    # Split into features and target
    X = df.drop('Churn', axis=1)
    y = df['Churn']
    
    # Identify categorical and numerical columns
    categorical_cols = X.select_dtypes(include=['object']).columns
    numerical_cols = X.select_dtypes(include=['int64', 'float64']).columns
    
    # Split the data
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    
    return X_train, X_test, y_train, y_test, categorical_cols, numerical_cols

# Build and evaluate models
def build_models(X_train, X_test, y_train, y_test, categorical_cols, numerical_cols):
    # Create preprocessor
    preprocessor = ColumnTransformer(
        transformers=[
            ('num', Pipeline(steps=[
                ('imputer', SimpleImputer(strategy='median')),
                ('scaler', StandardScaler())
            ]), numerical_cols),
            ('cat', Pipeline(steps=[
                ('imputer', SimpleImputer(strategy='most_frequent')),
                ('onehot', OneHotEncoder(handle_unknown='ignore'))
            ]), categorical_cols)
        ])
    
    # Create a dictionary to store model results
    model_results = {}
    
    # Random Forest
    rf_pipeline = Pipeline(steps=[
        ('preprocessor', preprocessor),
        ('classifier', RandomForestClassifier(random_state=42))
    ])
    
    rf_params = {
        'classifier__n_estimators': [100, 200],
        'classifier__max_depth': [None, 10, 20],
        'classifier__min_samples_split': [2, 5]
    }
    
    rf_grid = GridSearchCV(rf_pipeline, rf_params, cv=5, scoring='roc_auc')
    rf_grid.fit(X_train, y_train)
    
    best_rf = rf_grid.best_estimator_
    y_pred_rf = best_rf.predict(X_test)
    y_prob_rf = best_rf.predict_proba(X_test)[:, 1]
    
    model_results['random_forest'] = {
        'best_params': rf_grid.best_params_,
        'accuracy': accuracy_score(y_test, y_pred_rf),
        'classification_report': classification_report(y_test, y_pred_rf, output_dict=True),
        'roc_auc': roc_auc_score(y_test, y_prob_rf)
    }
    
    # Gradient Boosting
    gb_pipeline = Pipeline(steps=[
        ('preprocessor', preprocessor),
        ('classifier', GradientBoostingClassifier(random_state=42))
    ])
    
    gb_params = {
        'classifier__n_estimators': [100, 200],
        'classifier__learning_rate': [0.05, 0.1],
        'classifier__max_depth': [3, 5]
    }
    
    gb_grid = GridSearchCV(gb_pipeline, gb_params, cv=5, scoring='roc_auc')
    gb_grid.fit(X_train, y_train)
    
    best_gb = gb_grid.best_estimator_
    y_pred_gb = best_gb.predict(X_test)
    y_prob_gb = best_gb.predict_proba(X_test)[:, 1]
    
    model_results['gradient_boosting'] = {
        'best_params': gb_grid.best_params_,
        'accuracy': accuracy_score(y_test, y_pred_gb),
        'classification_report': classification_report(y_test, y_pred_gb, output_dict=True),
        'roc_auc': roc_auc_score(y_test, y_prob_gb)
    }
    
    # Logistic Regression
    lr_pipeline = Pipeline(steps=[
        ('preprocessor', preprocessor),
        ('classifier', LogisticRegression(random_state=42, max_iter=1000))
    ])
    
    lr_params = {
        'classifier__C': [0.1, 1.0, 10.0],
        'classifier__penalty': ['l2']
    }
    
    lr_grid = GridSearchCV(lr_pipeline, lr_params, cv=5, scoring='roc_auc')
    lr_grid.fit(X_train, y_train)
    
    best_lr = lr_grid.best_estimator_
    y_pred_lr = best_lr.predict(X_test)
    y_prob_lr = best_lr.predict_proba(X_test)[:, 1]
    
    model_results['logistic_regression'] = {
        'best_params': lr_grid.best_params_,
        'accuracy': accuracy_score(y_test, y_pred_lr),
        'classification_report': classification_report(y_test, y_pred_lr, output_dict=True),
        'roc_auc': roc_auc_score(y_test, y_prob_lr)
    }
    
    # Find the best model
    best_model_name = max(model_results, key=lambda x: model_results[x]['roc_auc'])
    best_model = {'name': best_model_name, **model_results[best_model_name]}
    
    # Get ROC curve data for visualization
    roc_data = {}
    for model_name, pipeline in zip(
        ['random_forest', 'gradient_boosting', 'logistic_regression'],
        [best_rf, best_gb, best_lr]
    ):
        y_prob = pipeline.predict_proba(X_test)[:, 1]
        fpr, tpr, _ = roc_curve(y_test, y_prob)
        roc_data[model_name] = {
            'fpr': fpr.tolist(),
            'tpr': tpr.tolist()
        }
    
    return best_model, model_results, roc_data, best_rf, preprocessor, categorical_cols, numerical_cols

# Feature importance analysis
def feature_importance(model, categorical_cols, numerical_cols, preprocessor):
    # For Random Forest or Gradient Boosting
    if hasattr(model, 'feature_importances_'):
        feature_importances = model.feature_importances_
        feature_names = list(numerical_cols)
        
        # Handle different scikit-learn versions for accessing transformers
        try:
            # Try the named_transformers_ attribute (newer versions)
            if hasattr(preprocessor, 'named_transformers_'):
                ohe = preprocessor.named_transformers_['cat'].named_steps['onehot']
            # Try the transformers attribute (older versions)
            elif hasattr(preprocessor, 'transformers'):
                # Find the transformer with name 'cat'
                for name, transformer, _ in preprocessor.transformers:
                    if name == 'cat':
                        ohe = transformer.named_steps['onehot']
                        break
            else:
                # Fallback: just return importances for numerical features
                print("Warning: Could not find categorical transformer. Showing limited feature importances.")
                importance_dict = dict(zip(feature_names, feature_importances[:len(feature_names)]))
                return dict(sorted(importance_dict.items(), key=lambda x: x[1], reverse=True)[:15])
            
            # Get feature names after one-hot encoding
            if hasattr(ohe, 'get_feature_names_out'):
                cat_features = ohe.get_feature_names_out(categorical_cols).tolist()
            elif hasattr(ohe, 'get_feature_names'):  # For older sklearn versions
                cat_features = ohe.get_feature_names(categorical_cols).tolist()
            else:
                # Fallback for very old versions or when methods not available
                cat_features = [f"{col}_{val}" for col in categorical_cols 
                            for val in ohe.categories_[list(categorical_cols).index(col)]]
            
            feature_names.extend(cat_features)
        except Exception as e:
            print(f"Warning: Error accessing transformers: {e}")
            # Provide simplified feature importance if error occurs
            return {f"Feature_{i}": imp for i, imp in enumerate(feature_importances[:15])}
        
        # Create dictionary of feature importances
        # Handle length mismatch by truncating to shortest length
        min_length = min(len(feature_names), len(feature_importances))
        importance_dict = dict(zip(feature_names[:min_length], feature_importances[:min_length]))
        
        # Sort by importance
        sorted_importances = dict(sorted(importance_dict.items(), key=lambda x: x[1], reverse=True)[:15])
        
        return sorted_importances
    
    return {}

# Save results to JSON file
def save_results(eda_results, best_model, model_results, roc_data, feature_importances):
    results = {
        'eda': eda_results,
        'best_model': best_model,
        'all_models': model_results,
        'roc_data': roc_data,
        'feature_importances': feature_importances
    }
    
    with open('churn_analysis_results.json', 'w') as f:
        json.dump(results, f)
    
    print("Results saved to churn_analysis_results.json")
    return results

# Create a prediction function that can be used by the frontend
def create_predictor(model, preprocessor, categorical_cols, numerical_cols):
    def predict_churn(customer_data):
        # Convert customer data dictionary to DataFrame
        df = pd.DataFrame([customer_data])
        
        # Ensure all categorical features are included
        for col in categorical_cols:
            if col not in df.columns:
                df[col] = None
        
        # Ensure all numerical features are included
        for col in numerical_cols:
            if col not in df.columns:
                df[col] = 0
            else:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Make prediction
        X = df[list(categorical_cols) + list(numerical_cols)]
        prediction_proba = model.predict_proba(X)[0, 1]
        prediction_label = 'Yes' if prediction_proba >= 0.5 else 'No'
        
        return {
            'probability': float(prediction_proba),
            'prediction': prediction_label
        }
    
    return predict_churn

# Main execution function
def run_churn_analysis(filepath):
    # Load data
    df = load_data(filepath)
    
    # Exploratory Data Analysis
    eda_results = explore_data(df)
    
    # Preprocess data
    X_train, X_test, y_train, y_test, categorical_cols, numerical_cols = preprocess_data(df)
    
    # Build and evaluate models
    best_model, model_results, roc_data, best_model_pipeline, preprocessor, cat_cols, num_cols = build_models(
        X_train, X_test, y_train, y_test, categorical_cols, numerical_cols)
    
    # Feature importance
    feature_importances = feature_importance(
        best_model_pipeline.named_steps['classifier'], cat_cols, num_cols, preprocessor)
    
    # Save results
    results = save_results(eda_results, best_model, model_results, roc_data, feature_importances)
    
    # Create predictor function
    predictor = create_predictor(best_model_pipeline, preprocessor, cat_cols, num_cols)
    
    return results, predictor

# If run as a script
if __name__ == "__main__":
    filepath = "Telco-Customer-Churn.csv"  # Change to your local path
    results, predictor = run_churn_analysis(filepath)
    
    # Example of using the predictor
    example_customer = {
        'gender': 'Male',
        'SeniorCitizen': 0,
        'Partner': 'Yes',
        'Dependents': 'No',
        'tenure': 36,
        'PhoneService': 'Yes',
        'MultipleLines': 'Yes',
        'InternetService': 'Fiber optic',
        'OnlineSecurity': 'No',
        'OnlineBackup': 'No',
        'DeviceProtection': 'Yes',
        'TechSupport': 'No',
        'StreamingTV': 'Yes',
        'StreamingMovies': 'Yes',
        'Contract': 'Month-to-month',
        'PaperlessBilling': 'Yes',
        'PaymentMethod': 'Electronic check',
        'MonthlyCharges': 95.7,
        'TotalCharges': 3455.3
    }
    
    prediction = predictor(example_customer)
    print(f"Churn prediction for example customer: {prediction['prediction']} (Probability: {prediction['probability']:.2f})")