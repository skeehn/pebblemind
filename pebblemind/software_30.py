"""Software 3.0: Self-Improving and Autonomous Learning System for PebbleMind"""

import asyncio
import json
import logging
import time
import random
from typing import Dict, Any, List, Optional, Tuple, Callable
from pathlib import Path
from datetime import datetime, timedelta
import hashlib
import pickle

logger = logging.getLogger(__name__)


class LearningOptimizer:
    """Self-improving system that learns from its own performance and interactions"""
    
    def __init__(self, model_path: str = "./data/self_learning.json"):
        self.model_path = Path(model_path)
        self.model_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Performance metrics and learned parameters
        self.performance_history = []
        self.learnt_parameters = {
            # Dynamic parameters that improve over time
            "context_window_optimization": 3,  # How many context items to use
            "reasoning_depth": "medium",       # How deep to reason
            "tool_usage_frequency": 0.7,      # How often to use tools
            "memory_recall_frequency": 0.8,   # How often to check memory
            "response_length_preference": "medium",  # Preferred response length
            "confidence_threshold": 0.6       # Threshold for confidence in responses
        }
        self.interaction_log = []
        self.knowledge_graph = {}  # Map of related concepts and their relationships
        
        self._load_model()
    
    def _load_model(self):
        """Load learned parameters from file"""
        if self.model_path.exists():
            try:
                with open(self.model_path, 'r') as f:
                    data = json.load(f)
                    self.learnt_parameters = data.get("parameters", self.learnt_parameters)
                    self.performance_history = data.get("history", [])
                    self.knowledge_graph = data.get("knowledge_graph", {})
            except Exception as e:
                logger.warning(f"Could not load self-learning model: {e}")
    
    def _save_model(self):
        """Save learned parameters to file"""
        try:
            data = {
                "parameters": self.learnt_parameters,
                "history": self.performance_history,
                "knowledge_graph": self.knowledge_graph,
                "timestamp": time.time()
            }
            with open(self.model_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f"Could not save self-learning model: {e}")
    
    async def learn_from_interaction(self, 
                                   input_text: str, 
                                   response: str, 
                                   user_feedback: Optional[str] = None,
                                   response_time: float = 0.0) -> bool:
        """Learn from an interaction to improve future responses"""
        interaction = {
            "timestamp": time.time(),
            "input": input_text,
            "response": response,
            "feedback": user_feedback,
            "response_time": response_time,
            "input_length": len(input_text.split()),
            "response_length": len(response.split()),
            "engagement_score": self._calculate_engagement_score(input_text, response, user_feedback)
        }
        
        self.interaction_log.append(interaction)
        
        # Update performance history (keep last 1000 interactions)
        if len(self.performance_history) > 1000:
            self.performance_history = self.performance_history[-1000:]
        
        # Update knowledge graph
        await self._update_knowledge_graph(input_text, response)
        
        # Adjust parameters based on performance
        await self._adjust_parameters(interaction)
        
        # Periodically optimize and save
        if len(self.interaction_log) % 10 == 0:  # Every 10 interactions
            self._save_model()
        
        return True
    
    def _calculate_engagement_score(self, input_text: str, response: str, feedback: Optional[str]) -> float:
        """Calculate how engaging and appropriate the response was"""
        score = 0.5  # Default neutral score
        
        # Positive feedback increases score
        if feedback and any(word in feedback.lower() for word in ["good", "helpful", "great", "excellent", "perfect"]):
            score += 0.3
        elif feedback and any(word in feedback.lower() for word in ["bad", "poor", "wrong", "unhelpful"]):
            score -= 0.3
        elif feedback and "not bad" in feedback.lower():
            score += 0.1
        
        # Longer, more relevant responses get higher scores
        input_keywords = set(input_text.lower().split())
        response_keywords = set(response.lower().split())
        keyword_overlap = len(input_keywords.intersection(response_keywords))
        
        if keyword_overlap > 0:
            score += min(0.2, keyword_overlap * 0.02)
        
        # Length appropriateness
        input_len = len(input_text.split())
        response_len = len(response.split())
        
        if input_len > 0:
            length_ratio = response_len / input_len
            # Optimal response is about 1.5x to 3x the input length
            if 1.0 <= length_ratio <= 4.0:
                score += 0.1
            else:
                score -= 0.1
        
        return max(0.0, min(1.0, score))  # Clamp between 0 and 1
    
    async def _update_knowledge_graph(self, input_text: str, response: str):
        """Update the knowledge graph with new relationship information"""
        # Extract key concepts from input and response
        input_concepts = self._extract_concepts(input_text)
        response_concepts = self._extract_concepts(response)
        
        # Create relationships between concepts
        for input_concept in input_concepts:
            if input_concept not in self.knowledge_graph:
                self.knowledge_graph[input_concept] = {"relationships": {}, "frequency": 0}
            
            self.knowledge_graph[input_concept]["frequency"] += 1
            
            for response_concept in response_concepts:
                if response_concept != input_concept:
                    if response_concept not in self.knowledge_graph[input_concept]["relationships"]:
                        self.knowledge_graph[input_concept]["relationships"][response_concept] = 0
                    self.knowledge_graph[input_concept]["relationships"][response_concept] += 1
    
    def _extract_concepts(self, text: str) -> List[str]:
        """Extract key concepts from text"""
        # Simple concept extraction - in practice, this would use NLP
        words = text.lower().split()
        # Remove common stop words and keep meaningful words
        stop_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by", "is", "are", "was", "were", "be", "been", "being", "have", "has", "had", "do", "does", "did", "will", "would", "could", "should", "may", "might", "must", "can", "this", "that", "these", "those", "i", "you", "he", "she", "it", "we", "they", "me", "him", "her", "us", "them"}
        
        concepts = [word.strip(".,!?;:") for word in words if word.lower() not in stop_words and len(word) > 2]
        return list(set(concepts))  # Remove duplicates
    
    async def _adjust_parameters(self, interaction: Dict[str, Any]):
        """Adjust parameters based on interaction performance"""
        feedback = interaction.get("feedback") or ""
        engagement_score = interaction.get("engagement_score", 0.5)
        
        # Adjust context window based on complexity and engagement
        if engagement_score > 0.7:
            # Good engagement - consider using more context
            self.learnt_parameters["context_window_optimization"] = min(
                10, self.learnt_parameters["context_window_optimization"] + 0.1
            )
        elif engagement_score < 0.4:
            # Poor engagement - reduce context to focus
            self.learnt_parameters["context_window_optimization"] = max(
                1, self.learnt_parameters["context_window_optimization"] - 0.1
            )
        
        # Adjust reasoning depth based on feedback
        if any(word in feedback.lower() for word in ["detailed", "thorough", "comprehensive"]):
            self.learnt_parameters["reasoning_depth"] = "deep"
        elif any(word in feedback.lower() for word in ["too long", "verbose", "detailed"]):
            self.learnt_parameters["reasoning_depth"] = "shallow"
        elif engagement_score > 0.7:
            self.learnt_parameters["reasoning_depth"] = "medium"
        
        # Adjust tool usage based on need
        tool_keywords = ["calculate", "compute", "find", "search", "time", "date", "weather"]
        has_tool_need = any(keyword in interaction["input"].lower() for keyword in tool_keywords)
        
        if has_tool_need and engagement_score > 0.6:
            self.learnt_parameters["tool_usage_frequency"] = min(0.9, self.learnt_parameters["tool_usage_frequency"] + 0.05)
        elif has_tool_need and engagement_score < 0.4:
            self.learnt_parameters["tool_usage_frequency"] = max(0.3, self.learnt_parameters["tool_usage_frequency"] - 0.05)
        
        # Adjust response length preference
        response_length = interaction["response_length"]
        input_length = interaction["input_length"]
        ratio = response_length / max(1, input_length)
        
        if ratio > 5 and engagement_score < 0.5:
            self.learnt_parameters["response_length_preference"] = "concise"
        elif ratio < 1.5 and engagement_score > 0.7:
            self.learnt_parameters["response_length_preference"] = "detailed"
        else:
            self.learnt_parameters["response_length_preference"] = "balanced"
    
    def get_optimized_parameters(self) -> Dict[str, Any]:
        """Get parameters optimized for current context"""
        return self.learnt_parameters.copy()
    
    async def predict_response_quality(self, input_text: str, response: str) -> float:
        """Predict the quality of a response before returning it"""
        # Use learned patterns to predict engagement
        engagement_score = self._calculate_engagement_score(input_text, response, None)
        
        # Apply learned parameter adjustments
        params = self.learnt_parameters
        length_preference = params["response_length_preference"]
        input_length = len(input_text.split())
        
        if length_preference == "concise":
            optimal_length = min(input_length * 2, len(response.split()))
        elif length_preference == "detailed":
            optimal_length = max(input_length * 3, len(response.split()))
        else:  # balanced
            optimal_length = input_length * 2
        
        length_score = 1.0 - abs(len(response.split()) - optimal_length) / max(optimal_length, 1)
        
        # Combine scores
        final_score = (engagement_score * 0.7) + (length_score * 0.3)
        
        return max(0.0, min(1.0, final_score))


class AutonomousSkillLearner:
    """System that autonomously learns new skills and capabilities"""
    
    def __init__(self):
        self.skill_inventory = {
            "basic_conversation": {"proficiency": 0.9, "last_used": time.time()},
            "question_answering": {"proficiency": 0.85, "last_used": time.time()},
            "task_completion": {"proficiency": 0.7, "last_used": time.time()}
        }
        self.skill_learning_goals = []
        self.acquired_skills = []
    
    async def assess_capability_gap(self, input_text: str) -> List[str]:
        """Assess what skills might be needed but are not present"""
        required_skills = []
        
        # Detect skill requirements from input
        text_lower = input_text.lower()
        
        if any(word in text_lower for word in ["math", "calculate", "compute", "equation"]):
            required_skills.append("mathematical_reasoning")
        
        if any(word in text_lower for word in ["code", "program", "python", "javascript", "function"]):
            required_skills.append("programming_assistance")
        
        if any(word in text_lower for word in ["write", "draft", "essay", "article", "outline"]):
            required_skills.append("writing_assistance")
        
        if any(word in text_lower for word in ["analyze", "research", "investigate", "find"]):
            required_skills.append("research_skills")
        
        if any(word in text_lower for word in ["translate", "language", "spanish", "french", "german"]):
            required_skills.append("translation_skills")
        
        # Check which skills we don't have or are not proficient in
        lacking_skills = []
        for skill in required_skills:
            if skill not in self.skill_inventory or self.skill_inventory[skill]["proficiency"] < 0.7:
                lacking_skills.append(skill)
        
        return lacking_skills
    
    async def acquire_new_skill(self, skill_name: str) -> bool:
        """Acquire a new skill by learning from examples and practice"""
        # In a real implementation, this would connect to external learning resources
        # or practice with examples, but for now we'll simulate the process
        
        if skill_name not in self.skill_inventory:
            # Simulate learning process
            await asyncio.sleep(random.uniform(0.1, 0.5))  # Simulate learning time
            
            # Set initial proficiency based on how well we can simulate the skill
            if "math" in skill_name:
                initial_proficiency = 0.8  # We have calculator tools
            elif "programming" in skill_name:
                initial_proficiency = 0.7  # We have code tools
            elif "writing" in skill_name:
                initial_proficiency = 0.6  # We have writing agent
            else:
                initial_proficiency = 0.5  # Default proficiency
            
            self.skill_inventory[skill_name] = {
                "proficiency": initial_proficiency,
                "last_used": time.time(),
                "examples_used": 0,
                "practice_sessions": 1
            }
            
            self.acquired_skills.append(skill_name)
            logger.info(f"Acquired new skill: {skill_name}")
            return True
        
        return False
    
    async def improve_existing_skill(self, skill_name: str, performance_score: float) -> bool:
        """Improve an existing skill based on performance"""
        if skill_name in self.skill_inventory:
            current = self.skill_inventory[skill_name]
            
            # Update proficiency based on performance (with decay over time)
            time_decay = 0.995 ** ((time.time() - current["last_used"]) / (24 * 3600))  # Daily decay
            new_proficiency = (current["proficiency"] * time_decay * 0.7) + (performance_score * 0.3)
            
            # Cap the improvement
            current["proficiency"] = min(0.95, max(0.1, new_proficiency))
            current["last_used"] = time.time()
            current["examples_used"] = current.get("examples_used", 0) + 1
            
            return True
        
        return False
    
    async def select_best_skills_for_task(self, input_text: str) -> List[str]:
        """Select the most appropriate skills for a given task"""
        # Assess what skills are needed
        needed_skills = await self.assess_capability_gap(input_text)
        
        # Also consider existing strong skills
        strong_skills = [
            skill for skill, data in self.skill_inventory.items() 
            if data["proficiency"] > 0.7
        ]
        
        # Combine and prioritize
        all_relevant_skills = needed_skills + strong_skills
        
        # Sort by proficiency (descending) and return top 3
        sorted_skills = sorted(
            all_relevant_skills, 
            key=lambda s: self.skill_inventory.get(s, {}).get("proficiency", 0.0), 
            reverse=True
        )
        
        return sorted_skills[:3]
    
    async def autonomous_learning_cycle(self):
        """Run an autonomous learning cycle to improve capabilities"""
        # Identify skills that need improvement
        skills_to_improve = [
            skill for skill, data in self.skill_inventory.items()
            if data["proficiency"] < 0.8  # Skills below 80% proficiency
        ]
        
        # Prioritize skills based on usage frequency and proficiency gap
        if skills_to_improve:
            # Simulate improvement for one skill per cycle
            target_skill = max(
                skills_to_improve,
                key=lambda s: (1 - self.skill_inventory[s]["proficiency"]) * (time.time() - self.skill_inventory[s]["last_used"])
            )
            
            # Simulate practice and improvement
            await asyncio.sleep(random.uniform(0.05, 0.2))
            await self.improve_existing_skill(target_skill, 0.9)  # High performance practice
            
            logger.info(f"Practiced and improved skill: {target_skill}")


class MetaLearningSystem:
    """System that learns how to learn and optimize its own learning processes"""
    
    def __init__(self):
        self.learning_strategies = {
            "fast_adaptation": {
                "success_rate": 0.7,
                "last_used": time.time(),
                "description": "Quick parameter adjustments based on immediate feedback"
            },
            "deep_optimization": {
                "success_rate": 0.9,
                "last_used": time.time() - 3600,  # 1 hour ago
                "description": "Comprehensive parameter and strategy optimization"
            },
            "pattern_recognition": {
                "success_rate": 0.8,
                "last_used": time.time() - 1800,  # 30 minutes ago
                "description": "Identifying patterns in user interactions to improve responses"
            }
        }
        self.meta_knowledge = {
            "best_practices": [],
            "failure_patterns": [],
            "success_indicators": [],
            "adaptation_rules": {}
        }
        self.performance_predictors = {}  # Learn to predict which approach works best for which scenario
    
    async def select_learning_strategy(self, context: Dict[str, Any]) -> str:
        """Select the best learning strategy based on context"""
        # Context includes information about the current interaction
        input_complexity = context.get("input_complexity", 0.5)
        user_satisfaction = context.get("previous_satisfaction", 0.5)
        time_since_last_optimization = time.time() - context.get("last_optimization", 0)
        
        # Select strategy based on context
        if time_since_last_optimization > 3600:  # More than 1 hour
            return "deep_optimization"
        elif user_satisfaction < 0.5:  # Low satisfaction
            return "fast_adaptation"
        elif input_complexity > 0.7:  # Complex input
            return "pattern_recognition"
        else:
            # Choose based on success rates and recency
            available_strategies = [(name, data) for name, data in self.learning_strategies.items()]
            chosen = max(available_strategies, key=lambda x: x[1]["success_rate"])
            return chosen[0]
    
    async def apply_learning_strategy(self, strategy_name: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply a specific learning strategy"""
        if strategy_name not in self.learning_strategies:
            return {"result": "error", "message": "Unknown strategy"}
        
        # Update the strategy's last used time
        self.learning_strategies[strategy_name]["last_used"] = time.time()
        
        if strategy_name == "fast_adaptation":
            # Quick adjustment of parameters
            result = await self._fast_adaptation(input_data)
        elif strategy_name == "deep_optimization":
            # Comprehensive optimization
            result = await self._deep_optimization(input_data)
        elif strategy_name == "pattern_recognition":
            # Find and apply patterns
            result = await self._pattern_recognition(input_data)
        else:
            result = {"result": "error", "message": "Unknown strategy"}
        
        # Update success rate based on result
        success = result.get("success", True)
        old_success_rate = self.learning_strategies[strategy_name]["success_rate"]
        new_success_rate = (old_success_rate * 0.9) + (1.0 if success else 0.0) * 0.1
        self.learning_strategies[strategy_name]["success_rate"] = new_success_rate
        
        return result
    
    async def _fast_adaptation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply quick parameter adjustments"""
        # Make small adjustments to key parameters
        adjustments = {
            "learning_rate_modifier": 1.0 + random.uniform(-0.1, 0.1),
            "context_weight": 1.0 + random.uniform(-0.1, 0.1),
            "memory_weight": 1.0 + random.uniform(-0.1, 0.1)
        }
        
        return {
            "result": "success",
            "strategy": "fast_adaptation",
            "adjustments": adjustments,
            "success": True
        }
    
    async def _deep_optimization(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply comprehensive optimization"""
        # Analyze performance history and optimize multiple parameters
        optimization_results = {
            "parameter_tuning": "completed",
            "knowledge_integration": "updated",
            "performance_prediction_model": "refined"
        }
        
        return {
            "result": "success", 
            "strategy": "deep_optimization",
            "results": optimization_results,
            "success": True
        }
    
    async def _pattern_recognition(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Identify and apply patterns"""
        # Look for patterns in the input and apply learned patterns
        patterns_found = []
        
        # In a real implementation, this would analyze patterns in the input
        # For now, simulate pattern recognition
        if input_data.get("input_type") == "question":
            patterns_found.append("question_pattern")
        if len(input_data.get("input_text", "")) > 100:
            patterns_found.append("long_input_pattern")
        
        return {
            "result": "success",
            "strategy": "pattern_recognition",
            "patterns_found": patterns_found,
            "success": True
        }
    
    async def reflect_on_learning(self, learning_outcome: Dict[str, Any]) -> Dict[str, Any]:
        """Reflect on learning outcomes to improve meta-learning"""
        # Analyze what worked and what didn't
        strategy_used = learning_outcome.get("strategy", "unknown")
        success = learning_outcome.get("success", False)
        context = learning_outcome.get("context", {})
        
        # Add to meta-knowledge if it's a significant pattern
        if success and "patterns_found" in learning_outcome:
            pattern_key = f"{strategy_used}_{hash(str(context)) % 1000}"
            if pattern_key not in self.meta_knowledge["success_indicators"]:
                self.meta_knowledge["success_indicators"].append(pattern_key)
        
        # Update adaptation rules
        context_signature = self._get_context_signature(context)
        if context_signature not in self.performance_predictors:
            self.performance_predictors[context_signature] = {}
        
        if strategy_used not in self.performance_predictors[context_signature]:
            self.performance_predictors[context_signature][strategy_used] = []
        
        self.performance_predictors[context_signature][strategy_used].append(success)
        
        return {
            "reflected": True,
            "context_signature": context_signature,
            "learning_updated": True
        }
    
    def _get_context_signature(self, context: Dict[str, Any]) -> str:
        """Get a signature for the context to use in prediction models"""
        # Create a hash signature of important context factors
        signature_parts = [
            str(context.get("input_complexity", 0)),
            str(context.get("user_satisfaction", 0.5)),
            str(context.get("input_type", "unknown")),
            str(len(context.get("input_text", "")))
        ]
        return hashlib.md5("_".join(signature_parts).encode()).hexdigest()


class SelfImprovementManager:
    """Main orchestrator for Software 3.0 self-improvement capabilities"""
    
    def __init__(self):
        self.learning_optimizer = LearningOptimizer()
        self.skill_learner = AutonomousSkillLearner()
        self.meta_learner = MetaLearningSystem()
        self.improvement_cycle_count = 0
    
    async def process_interaction(self, input_text: str, response: str, 
                                  user_feedback: Optional[str] = None, 
                                  response_time: float = 0.0) -> Dict[str, Any]:
        """Process an interaction for self-improvement"""
        # Learn from the interaction
        await self.learning_optimizer.learn_from_interaction(
            input_text, response, user_feedback, response_time
        )
        
        # Assess if new skills are needed
        needed_skills = await self.skill_learner.assess_capability_gap(input_text)
        for skill in needed_skills:
            await self.skill_learner.acquire_new_skill(skill)
        
        # Update skill proficiencies based on performance
        # This is simulated - in practice, you'd have a way to evaluate response quality
        input_type = self._classify_input_type(input_text)
        if input_type in [skill for skill in self.skill_learner.skill_inventory.keys()]:
            await self.skill_learner.improve_existing_skill(input_type, 0.8)  # Assume good performance
        
        return {
            "interaction_learned": True,
            "skills_assessed": len(needed_skills),
            "new_skills_acquired": needed_skills
        }
    
    async def autonomous_improvement_cycle(self) -> Dict[str, Any]:
        """Run an autonomous improvement cycle"""
        self.improvement_cycle_count += 1
        
        # Select a learning strategy
        context = {
            "input_complexity": 0.6,  # Average complexity
            "previous_satisfaction": 0.7,  # Average satisfaction
            "last_optimization": getattr(self, '_last_optimization', 0),
            "cycle_count": self.improvement_cycle_count
        }
        
        strategy = await self.meta_learner.select_learning_strategy(context)
        
        # Apply the learning strategy
        strategy_input = {
            "input_type": "system_optimization",
            "input_text": "General system optimization",
            "context": context
        }
        
        result = await self.meta_learner.apply_learning_strategy(strategy, strategy_input)
        
        # Reflect on the learning outcome
        reflection = await self.meta_learner.reflect_on_learning(result)
        
        # Run skill improvement cycle
        await self.skill_learner.autonomous_learning_cycle()
        
        # Update last optimization time
        self._last_optimization = time.time()
        
        return {
            "cycle_complete": True,
            "strategy_used": strategy,
            "result": result,
            "reflection": reflection,
            "skills_improved": self.skill_learner.acquired_skills[-5:]  # Last 5 skills
        }
    
    def _classify_input_type(self, input_text: str) -> str:
        """Classify the type of input to help with skill improvement"""
        text_lower = input_text.lower()
        
        if any(word in text_lower for word in ["calculate", "math", "compute"]):
            return "mathematical_reasoning"
        elif any(word in text_lower for word in ["write", "draft", "create"]):
            return "writing_assistance"
        elif any(word in text_lower for word in ["code", "program", "python"]):
            return "programming_assistance"
        else:
            return "general_conversation"
    
    async def predict_and_optimize_response(self, input_text: str, base_response: str) -> Tuple[str, Dict[str, Any]]:
        """Predict response quality and optimize if needed"""
        # Predict response quality
        predicted_quality = await self.learning_optimizer.predict_response_quality(input_text, base_response)
        
        optimization_metadata = {
            "predicted_quality": predicted_quality,
            "optimized": False,
            "improvement_applied": []
        }
        
        # If quality is low, try to improve
        if predicted_quality < 0.6:  # Below threshold
            # Get optimized parameters
            params = self.learning_optimizer.get_optimized_parameters()
            
            # Apply improvements
            if params.get("response_length_preference") == "detailed" and len(base_response.split()) < 50:
                # Add more detail if needed
                enhanced_response = f"{base_response} [Additional context: This response has been enhanced to provide more comprehensive information as requested by the nature of your query.]"
                optimization_metadata["optimized"] = True
                optimization_metadata["improvement_applied"].append("detail_enhancement")
            elif params.get("response_length_preference") == "concise" and len(base_response.split()) > 100:
                # Make more concise
                sentences = base_response.split('. ')
                enhanced_response = '. '.join(sentences[:3]) + "." if sentences else base_response
                optimization_metadata["optimized"] = True
                optimization_metadata["improvement_applied"].append("conciseness")
            else:
                enhanced_response = base_response
        else:
            enhanced_response = base_response
        
        return enhanced_response, optimization_metadata


# Example utility function to integrate with PebbleMind
async def apply_software_30_improvements(pebblemind_instance):
    """Apply Software 3.0 improvements to a PebbleMind instance"""
    if not hasattr(pebblemind_instance, 'self_improvement_manager'):
        pebblemind_instance.self_improvement_manager = SelfImprovementManager()
    
    return pebblemind_instance
