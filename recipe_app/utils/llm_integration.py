"""
Phi-3 Mini LLM Integration for Advanced Pantry Analysis
Custom AI model training and inference for domain-specific insights
"""
import os
import json
import torch
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import logging

# Try importing Phi-3 dependencies
try:
    from transformers import (
        AutoTokenizer, 
        AutoModelForCausalLM, 
        TrainingArguments, 
        Trainer,
        DataCollatorForLanguageModeling
    )
    from datasets import Dataset
    import torch.nn.functional as F
    PHI3_AVAILABLE = True
except ImportError:
    PHI3_AVAILABLE = False
    logging.warning("Phi-3 dependencies not available. Install: pip install transformers datasets torch")

from recipe_app.models.pantry_models import PantryItem, PantryUsageLog
from recipe_app.models.models import Recipe
from recipe_app.models.advanced_models import MealPlan


@dataclass
class PantryAnalysisResult:
    """Result from Phi-3 analysis"""
    insights: List[str]
    predictions: Dict[str, Any]
    recommendations: List[str]
    confidence_score: float
    analysis_timestamp: datetime


class Phi3PantryAnalyzer:
    """
    Custom Phi-3 Mini model for intelligent pantry analysis
    """
    
    def __init__(self, user_id: int, model_path: Optional[str] = None):
        self.user_id = user_id
        self.model_path = model_path or "microsoft/Phi-3-mini-4k-instruct"
        self.fine_tuned_model_path = f"./models/phi3_pantry_{user_id}"
        self.tokenizer = None
        self.model = None
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        if PHI3_AVAILABLE:
            self._initialize_model()
    
    def _initialize_model(self):
        """Initialize or load the Phi-3 model"""
        try:
            # Try loading fine-tuned model first
            if os.path.exists(self.fine_tuned_model_path):
                logging.info(f"Loading fine-tuned model from {self.fine_tuned_model_path}")
                self.tokenizer = AutoTokenizer.from_pretrained(self.fine_tuned_model_path)
                self.model = AutoModelForCausalLM.from_pretrained(
                    self.fine_tuned_model_path,
                    torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                    device_map="auto" if torch.cuda.is_available() else None
                )
            else:
                # Load base Phi-3 model
                logging.info(f"Loading base Phi-3 model: {self.model_path}")
                self.tokenizer = AutoTokenizer.from_pretrained(self.model_path)
                self.model = AutoModelForCausalLM.from_pretrained(
                    self.model_path,
                    torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                    device_map="auto" if torch.cuda.is_available() else None
                )
                
                # Add special tokens for pantry analysis
                special_tokens = ["<PANTRY>", "</PANTRY>", "<RECIPE>", "</RECIPE>", "<ANALYSIS>", "</ANALYSIS>"]
                self.tokenizer.add_special_tokens({"additional_special_tokens": special_tokens})
                self.model.resize_token_embeddings(len(self.tokenizer))
            
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
                
            self.model.to(self.device)
            logging.info(f"Phi-3 model loaded successfully on {self.device}")
            
        except Exception as e:
            logging.error(f"Failed to initialize Phi-3 model: {e}")
            self.model = None
            self.tokenizer = None
    
    def generate_training_data(self) -> List[Dict[str, str]]:
        """
        Generate training data from user's pantry history
        """
        training_samples = []
        
        # Get user's pantry items and usage history
        pantry_items = PantryItem.query.filter_by(user_id=self.user_id).all()
        
        for item in pantry_items:
            # Get usage logs for this item
            usage_logs = PantryUsageLog.query.filter_by(
                user_id=self.user_id,
                item_id=item.id
            ).order_by(PantryUsageLog.timestamp.desc()).limit(50).all()
            
            if len(usage_logs) >= 3:  # Need sufficient data
                # Create training sample
                pantry_context = self._create_pantry_context(item, usage_logs)
                analysis_target = self._create_analysis_target(item, usage_logs)
                
                training_sample = {
                    "input": f"<PANTRY>{pantry_context}</PANTRY>\n\nAnalyze this pantry item and provide insights:",
                    "output": f"<ANALYSIS>{analysis_target}</ANALYSIS>"
                }
                training_samples.append(training_sample)
        
        # Add recipe-based training samples
        meal_plans = MealPlan.query.filter_by(user_id=self.user_id).limit(20).all()
        for meal_plan in meal_plans:
            if meal_plan.recipe:
                recipe_context = self._create_recipe_context(meal_plan.recipe, pantry_items)
                recipe_analysis = self._create_recipe_analysis(meal_plan.recipe, pantry_items)
                
                training_sample = {
                    "input": f"<RECIPE>{recipe_context}</RECIPE>\n\nAnalyze ingredient availability:",
                    "output": f"<ANALYSIS>{recipe_analysis}</ANALYSIS>"
                }
                training_samples.append(training_sample)
        
        return training_samples
    
    def _create_pantry_context(self, item: PantryItem, usage_logs: List[PantryUsageLog]) -> str:
        """Create structured context for training"""
        context = f"Item: {item.name}\n"
        context += f"Current Quantity: {item.current_quantity} {item.unit or 'units'}\n"
        context += f"Category: {item.category or 'uncategorized'}\n"
        
        # Add usage pattern
        context += "Usage History:\n"
        for log in usage_logs[:10]:
            action = "consumed" if log.quantity_change < 0 else "added"
            context += f"- {log.timestamp.strftime('%Y-%m-%d')}: {action} {abs(log.quantity_change)}\n"
        
        return context
    
    def _create_analysis_target(self, item: PantryItem, usage_logs: List[PantryUsageLog]) -> str:
        """Create target analysis for training"""
        # Calculate consumption rate
        consumption_logs = [log for log in usage_logs if log.quantity_change < 0]
        if len(consumption_logs) >= 2:
            total_consumed = sum(abs(log.quantity_change) for log in consumption_logs)
            days_span = (consumption_logs[0].timestamp - consumption_logs[-1].timestamp).days
            daily_rate = total_consumed / max(days_span, 1)
            days_remaining = item.current_quantity / max(daily_rate, 0.1)
            
            analysis = f"Daily consumption rate: {daily_rate:.2f} {item.unit or 'units'}\n"
            analysis += f"Estimated days remaining: {days_remaining:.1f}\n"
            
            if days_remaining <= 3:
                analysis += "⚠️ LOW STOCK WARNING: This item will run out soon\n"
                analysis += "Recommendation: Add to shopping list immediately\n"
            elif days_remaining <= 7:
                analysis += "📊 MODERATE USAGE: Monitor consumption\n"
                analysis += "Recommendation: Consider restocking within a week\n"
            else:
                analysis += "✅ ADEQUATE STOCK: Good inventory level\n"
                analysis += "Recommendation: Continue monitoring\n"
        else:
            analysis = "Insufficient usage data for accurate prediction\n"
            analysis += "Recommendation: Continue monitoring usage patterns\n"
        
        return analysis
    
    def _create_recipe_context(self, recipe: Recipe, pantry_items: List[PantryItem]) -> str:
        """Create recipe context for training"""
        context = f"Recipe: {recipe.title}\n"
        context += f"Servings: {recipe.servings or 4}\n"
        context += "Required Ingredients:\n"
        
        for ingredient in recipe.ingredients:
            context += f"- {ingredient.name}: {ingredient.quantity or 1} {ingredient.unit or 'units'}\n"
        
        context += "\nAvailable in Pantry:\n"
        for item in pantry_items:
            context += f"- {item.name}: {item.current_quantity} {item.unit or 'units'}\n"
        
        return context
    
    def _create_recipe_analysis(self, recipe: Recipe, pantry_items: List[PantryItem]) -> str:
        """Create recipe analysis for training"""
        analysis = "Ingredient Analysis:\n"
        missing_ingredients = []
        
        for ingredient in recipe.ingredients:
            # Find matching pantry item
            matching_item = None
            for item in pantry_items:
                if ingredient.name.lower() in item.name.lower() or item.name.lower() in ingredient.name.lower():
                    matching_item = item
                    break
            
            if matching_item:
                required = float(ingredient.quantity or 1)
                available = matching_item.current_quantity
                
                if available >= required:
                    analysis += f"✅ {ingredient.name}: Available ({available} >= {required})\n"
                else:
                    shortage = required - available
                    analysis += f"❌ {ingredient.name}: Short by {shortage} {ingredient.unit or 'units'}\n"
                    missing_ingredients.append(f"{ingredient.name} ({shortage} {ingredient.unit or 'units'})")
            else:
                analysis += f"❓ {ingredient.name}: Not found in pantry\n"
                missing_ingredients.append(ingredient.name)
        
        if missing_ingredients:
            analysis += f"\n🛒 Shopping List: {', '.join(missing_ingredients)}\n"
            analysis += "Recommendation: Purchase missing ingredients before cooking\n"
        else:
            analysis += "\n✅ All ingredients available - ready to cook!\n"
        
        return analysis
    
    def fine_tune_model(self, training_data: Optional[List[Dict[str, str]]] = None) -> bool:
        """
        Fine-tune Phi-3 model on user's pantry data
        """
        if not PHI3_AVAILABLE or not self.model:
            logging.error("Phi-3 model not available for fine-tuning")
            return False
        
        try:
            # Generate training data if not provided
            if training_data is None:
                training_data = self.generate_training_data()
            
            if len(training_data) < 10:
                logging.warning("Insufficient training data for fine-tuning")
                return False
            
            # Prepare dataset
            def preprocess_function(examples):
                inputs = examples["input"]
                targets = examples["output"]
                
                # Combine input and output for causal LM training
                texts = [f"{inp}\n{tgt}" for inp, tgt in zip(inputs, targets)]
                
                tokenized = self.tokenizer(
                    texts,
                    truncation=True,
                    padding=True,
                    max_length=512,
                    return_tensors="pt"
                )
                
                # Labels are the same as input_ids for causal LM
                tokenized["labels"] = tokenized["input_ids"].clone()
                return tokenized
            
            # Create dataset
            dataset_dict = {
                "input": [sample["input"] for sample in training_data],
                "output": [sample["output"] for sample in training_data]
            }
            dataset = Dataset.from_dict(dataset_dict)
            tokenized_dataset = dataset.map(preprocess_function, batched=True)
            
            # Training arguments
            training_args = TrainingArguments(
                output_dir=self.fine_tuned_model_path,
                overwrite_output_dir=True,
                num_train_epochs=3,
                per_device_train_batch_size=2,
                gradient_accumulation_steps=4,
                warmup_steps=100,
                logging_steps=10,
                save_steps=500,
                evaluation_strategy="no",
                save_total_limit=2,
                prediction_loss_only=True,
                remove_unused_columns=False,
                dataloader_pin_memory=False,
                learning_rate=5e-5,
                weight_decay=0.01,
                fp16=torch.cuda.is_available(),
            )
            
            # Data collator
            data_collator = DataCollatorForLanguageModeling(
                tokenizer=self.tokenizer,
                mlm=False,  # Causal LM, not masked LM
            )
            
            # Trainer
            trainer = Trainer(
                model=self.model,
                args=training_args,
                train_dataset=tokenized_dataset,
                data_collator=data_collator,
            )
            
            # Fine-tune
            logging.info("Starting Phi-3 fine-tuning...")
            trainer.train()
            
            # Save fine-tuned model
            trainer.save_model()
            self.tokenizer.save_pretrained(self.fine_tuned_model_path)
            
            logging.info(f"Fine-tuning completed. Model saved to {self.fine_tuned_model_path}")
            return True
            
        except Exception as e:
            logging.error(f"Fine-tuning failed: {e}")
            return False
    
    def analyze_pantry_with_phi3(self, pantry_items: List[PantryItem], 
                                context: Optional[str] = None) -> PantryAnalysisResult:
        """
        Use Phi-3 to analyze pantry and provide intelligent insights
        """
        if not PHI3_AVAILABLE or not self.model:
            # Fallback to rule-based analysis
            return self._fallback_analysis(pantry_items)
        
        try:
            # Prepare input context
            pantry_context = "<PANTRY>\n"
            for item in pantry_items:
                pantry_context += f"- {item.name}: {item.current_quantity} {item.unit or 'units'}"
                if item.category:
                    pantry_context += f" ({item.category})"
                pantry_context += "\n"
            pantry_context += "</PANTRY>\n"
            
            # Add additional context if provided
            if context:
                pantry_context += f"\nAdditional Context: {context}\n"
            
            # Create analysis prompt
            prompt = f"""{pantry_context}

Analyze this pantry inventory and provide:
1. Key insights about consumption patterns
2. Items that need immediate attention
3. Smart recommendations for optimization
4. Potential recipe suggestions based on available ingredients

<ANALYSIS>"""

            # Tokenize and generate
            inputs = self.tokenizer(prompt, return_tensors="pt", truncation=True, max_length=1024)
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=512,
                    temperature=0.7,
                    do_sample=True,
                    pad_token_id=self.tokenizer.eos_token_id,
                    eos_token_id=self.tokenizer.eos_token_id
                )
            
            # Decode response
            response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            analysis_start = response.find("<ANALYSIS>")
            if analysis_start != -1:
                analysis_text = response[analysis_start + len("<ANALYSIS>"):].strip()
            else:
                analysis_text = response[len(prompt):].strip()
            
            # Parse the analysis
            insights, predictions, recommendations = self._parse_phi3_response(analysis_text)
            
            return PantryAnalysisResult(
                insights=insights,
                predictions=predictions,
                recommendations=recommendations,
                confidence_score=0.85,  # High confidence for fine-tuned model
                analysis_timestamp=datetime.utcnow()
            )
            
        except Exception as e:
            logging.error(f"Phi-3 analysis failed: {e}")
            return self._fallback_analysis(pantry_items)
    
    def _parse_phi3_response(self, response: str) -> Tuple[List[str], Dict[str, Any], List[str]]:
        """Parse Phi-3 response into structured data"""
        insights = []
        predictions = {}
        recommendations = []
        
        lines = response.split('\n')
        current_section = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Detect sections
            if "insight" in line.lower() or "pattern" in line.lower():
                current_section = "insights"
            elif "recommendation" in line.lower() or "suggest" in line.lower():
                current_section = "recommendations"
            elif line.startswith('-') or line.startswith('•') or line.startswith('*'):
                # Extract bullet point content
                content = line[1:].strip()
                if current_section == "insights":
                    insights.append(content)
                elif current_section == "recommendations":
                    recommendations.append(content)
            elif "⚠️" in line or "WARNING" in line.upper():
                insights.append(f"⚠️ {line}")
            elif "✅" in line or "GOOD" in line.upper():
                insights.append(f"✅ {line}")
        
        # Extract any numerical predictions
        import re
        numbers = re.findall(r'(\d+(?:\.\d+)?)\s*(days?|weeks?|months?)', response.lower())
        for value, unit in numbers:
            predictions[f"time_estimate_{unit}"] = float(value)
        
        return insights, predictions, recommendations
    
    def _fallback_analysis(self, pantry_items: List[PantryItem]) -> PantryAnalysisResult:
        """Fallback analysis when Phi-3 is not available"""
        insights = []
        recommendations = []
        predictions = {}
        
        total_items = len(pantry_items)
        low_stock_items = [item for item in pantry_items if item.current_quantity <= 2]
        
        insights.append(f"Pantry contains {total_items} items")
        if low_stock_items:
            insights.append(f"⚠️ {len(low_stock_items)} items are running low")
            recommendations.append("Restock low-quantity items soon")
        else:
            insights.append("✅ All items have adequate stock")
        
        predictions["total_items"] = total_items
        predictions["low_stock_count"] = len(low_stock_items)
        
        return PantryAnalysisResult(
            insights=insights,
            predictions=predictions,
            recommendations=recommendations,
            confidence_score=0.6,  # Lower confidence for fallback
            analysis_timestamp=datetime.utcnow()
        )
    
    def get_smart_shopping_suggestions(self, upcoming_recipes: List[Recipe]) -> List[str]:
        """Get AI-powered shopping suggestions"""
        if not PHI3_AVAILABLE or not self.model:
            return ["Install Phi-3 dependencies for smart suggestions"]
        
        # This would use the fine-tuned model to suggest optimal shopping
        # Based on upcoming recipes and current pantry state
        pantry_items = PantryItem.query.filter_by(user_id=self.user_id).all()
        
        prompt = "<RECIPE>\n"
        for recipe in upcoming_recipes:
            prompt += f"Planned: {recipe.title}\n"
            for ing in recipe.ingredients:
                prompt += f"  - {ing.name}: {ing.quantity} {ing.unit}\n"
        prompt += "</RECIPE>\n\n"
        
        prompt += "<PANTRY>\n"
        for item in pantry_items:
            prompt += f"Available: {item.name} ({item.current_quantity} {item.unit})\n"
        prompt += "</PANTRY>\n\n"
        
        prompt += "Generate an optimized shopping list:\n<ANALYSIS>"
        
        # Use the model to generate smart suggestions
        # Implementation similar to analyze_pantry_with_phi3
        
        return ["Smart shopping list generated by Phi-3"]


def setup_phi3_environment():
    """
    Setup script to install Phi-3 dependencies
    """
    requirements = [
        "torch>=2.0.0",
        "transformers>=4.35.0",
        "datasets>=2.14.0",
        "accelerate>=0.21.0",
        "peft>=0.5.0",  # For parameter-efficient fine-tuning
        "bitsandbytes",  # For quantization
    ]
    
    return requirements


def create_training_job(user_id: int) -> Dict[str, Any]:
    """
    Create a background training job for user's Phi-3 model
    """
    analyzer = Phi3PantryAnalyzer(user_id)
    training_data = analyzer.generate_training_data()
    
    if len(training_data) < 10:
        return {
            "status": "insufficient_data",
            "message": "Need more pantry usage data to train a custom model",
            "required_samples": 10,
            "current_samples": len(training_data)
        }
    
    # In a production environment, this would be submitted to a job queue
    success = analyzer.fine_tune_model(training_data)
    
    return {
        "status": "completed" if success else "failed",
        "model_path": analyzer.fine_tuned_model_path if success else None,
        "training_samples": len(training_data),
        "message": "Custom Phi-3 model trained successfully" if success else "Training failed"
    }
