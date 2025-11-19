"""Multi-agent collaboration system for complex tasks"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)


class AgentRole(Enum):
    """Agent roles in collaboration"""
    COORDINATOR = "coordinator"
    RESEARCHER = "researcher"
    ANALYZER = "analyzer"
    EXECUTOR = "executor"
    REVIEWER = "reviewer"


@dataclass
class Task:
    """Collaborative task"""
    id: str
    description: str
    assigned_to: Optional[str] = None
    status: str = "pending"  # pending, in_progress, completed, failed
    result: Any = None
    dependencies: List[str] = None
    metadata: Dict[str, Any] = None


@dataclass
class AgentMessage:
    """Message between agents"""
    from_agent: str
    to_agent: str
    message_type: str  # request, response, info, error
    content: Any
    timestamp: str


class CollaborativeAgent:
    """
    Base class for collaborative agents.

    Agents can communicate, delegate tasks, and work together.
    """

    def __init__(
        self,
        agent_id: str,
        role: AgentRole,
        capabilities: List[str]
    ):
        """
        Initialize collaborative agent

        Args:
            agent_id: Unique agent identifier
            role: Agent role
            capabilities: List of agent capabilities
        """
        self.agent_id = agent_id
        self.role = role
        self.capabilities = capabilities
        self._message_queue: asyncio.Queue = asyncio.Queue()
        self._running = False

    async def execute_task(self, task: Task) -> Any:
        """
        Execute task

        Args:
            task: Task to execute

        Returns:
            Task result
        """
        raise NotImplementedError("Subclasses must implement execute_task")

    async def send_message(
        self,
        to_agent: str,
        message_type: str,
        content: Any
    ):
        """Send message to another agent"""
        message = AgentMessage(
            from_agent=self.agent_id,
            to_agent=to_agent,
            message_type=message_type,
            content=content,
            timestamp=datetime.now().isoformat()
        )
        # Will be handled by coordinator
        return message

    async def receive_message(self, message: AgentMessage):
        """Receive message from another agent"""
        await self._message_queue.put(message)

    async def process_messages(self):
        """Process incoming messages"""
        while self._running:
            try:
                message = await asyncio.wait_for(
                    self._message_queue.get(),
                    timeout=1.0
                )
                await self._handle_message(message)
            except asyncio.TimeoutError:
                continue

    async def _handle_message(self, message: AgentMessage):
        """Handle incoming message"""
        logger.debug(f"Agent {self.agent_id} received message: {message}")


class AgentCoordinator:
    """
    Coordinates multiple agents to solve complex tasks.

    Features:
    - Task decomposition
    - Agent selection and assignment
    - Inter-agent communication
    - Result aggregation
    - Error handling and recovery
    """

    def __init__(self):
        """Initialize agent coordinator"""
        self._agents: Dict[str, CollaborativeAgent] = {}
        self._tasks: Dict[str, Task] = {}
        self._running = False

    def register_agent(self, agent: CollaborativeAgent):
        """
        Register agent with coordinator

        Args:
            agent: Agent to register
        """
        self._agents[agent.agent_id] = agent
        logger.info(f"Registered agent: {agent.agent_id} ({agent.role.value})")

    def unregister_agent(self, agent_id: str):
        """Unregister agent"""
        if agent_id in self._agents:
            del self._agents[agent_id]
            logger.info(f"Unregistered agent: {agent_id}")

    async def execute_collaborative_task(
        self,
        task_description: str,
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Execute complex task using multiple agents

        Args:
            task_description: High-level task description
            context: Task context

        Returns:
            Aggregated results from all agents
        """
        logger.info(f"Starting collaborative task: {task_description}")

        # Decompose task into subtasks
        subtasks = await self._decompose_task(task_description, context)

        # Assign subtasks to agents
        assignments = await self._assign_tasks(subtasks)

        # Execute subtasks in parallel with dependency management
        results = await self._execute_subtasks(assignments)

        # Aggregate results
        final_result = await self._aggregate_results(results)

        logger.info(f"Collaborative task completed: {task_description}")
        return final_result

    async def _decompose_task(
        self,
        task_description: str,
        context: Optional[Dict[str, Any]]
    ) -> List[Task]:
        """
        Decompose high-level task into subtasks

        Args:
            task_description: Task description
            context: Task context

        Returns:
            List of subtasks
        """
        # Simple decomposition - in real implementation, use LLM
        import uuid

        # For demo, create subtasks based on available agent roles
        subtasks = []

        # Research phase
        if any(agent.role == AgentRole.RESEARCHER for agent in self._agents.values()):
            subtasks.append(Task(
                id=str(uuid.uuid4()),
                description=f"Research: {task_description}",
                metadata={"phase": "research", "context": context}
            ))

        # Analysis phase
        if any(agent.role == AgentRole.ANALYZER for agent in self._agents.values()):
            subtasks.append(Task(
                id=str(uuid.uuid4()),
                description=f"Analyze: {task_description}",
                dependencies=[subtasks[0].id] if subtasks else None,
                metadata={"phase": "analysis", "context": context}
            ))

        # Execution phase
        if any(agent.role == AgentRole.EXECUTOR for agent in self._agents.values()):
            subtasks.append(Task(
                id=str(uuid.uuid4()),
                description=f"Execute: {task_description}",
                dependencies=[subtasks[-1].id] if subtasks else None,
                metadata={"phase": "execution", "context": context}
            ))

        # Review phase
        if any(agent.role == AgentRole.REVIEWER for agent in self._agents.values()):
            subtasks.append(Task(
                id=str(uuid.uuid4()),
                description=f"Review: {task_description}",
                dependencies=[subtasks[-1].id] if subtasks else None,
                metadata={"phase": "review", "context": context}
            ))

        return subtasks

    async def _assign_tasks(self, tasks: List[Task]) -> Dict[str, Task]:
        """
        Assign tasks to suitable agents

        Args:
            tasks: List of tasks

        Returns:
            Task assignments
        """
        assignments = {}

        for task in tasks:
            # Find suitable agent based on phase
            phase = task.metadata.get("phase", "")
            suitable_agents = []

            if phase == "research":
                suitable_agents = [
                    a for a in self._agents.values()
                    if a.role == AgentRole.RESEARCHER
                ]
            elif phase == "analysis":
                suitable_agents = [
                    a for a in self._agents.values()
                    if a.role == AgentRole.ANALYZER
                ]
            elif phase == "execution":
                suitable_agents = [
                    a for a in self._agents.values()
                    if a.role == AgentRole.EXECUTOR
                ]
            elif phase == "review":
                suitable_agents = [
                    a for a in self._agents.values()
                    if a.role == AgentRole.REVIEWER
                ]

            # Assign to first available agent
            if suitable_agents:
                agent = suitable_agents[0]
                task.assigned_to = agent.agent_id
                assignments[task.id] = task
                logger.debug(f"Assigned task {task.id} to agent {agent.agent_id}")
            else:
                logger.warning(f"No suitable agent for task: {task.id}")

        return assignments

    async def _execute_subtasks(
        self,
        assignments: Dict[str, Task]
    ) -> Dict[str, Any]:
        """
        Execute subtasks with dependency management

        Args:
            assignments: Task assignments

        Returns:
            Task results
        """
        results = {}
        completed = set()

        # Execute tasks respecting dependencies
        while len(completed) < len(assignments):
            # Find tasks ready to execute
            ready_tasks = [
                task for task_id, task in assignments.items()
                if task_id not in completed and
                (not task.dependencies or all(dep in completed for dep in task.dependencies))
            ]

            if not ready_tasks:
                logger.error("Circular dependency or no ready tasks!")
                break

            # Execute ready tasks in parallel
            task_futures = []
            for task in ready_tasks:
                if task.assigned_to and task.assigned_to in self._agents:
                    agent = self._agents[task.assigned_to]
                    future = agent.execute_task(task)
                    task_futures.append((task.id, future))

            # Wait for completion
            for task_id, future in task_futures:
                try:
                    result = await future
                    results[task_id] = result
                    completed.add(task_id)
                    logger.debug(f"Completed task: {task_id}")
                except Exception as e:
                    logger.error(f"Task {task_id} failed: {e}")
                    results[task_id] = {"error": str(e)}
                    completed.add(task_id)

        return results

    async def _aggregate_results(
        self,
        results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Aggregate results from all subtasks

        Args:
            results: Individual task results

        Returns:
            Aggregated result
        """
        return {
            "success": all("error" not in r for r in results.values()),
            "subtask_count": len(results),
            "results": results,
            "summary": self._generate_summary(results)
        }

    def _generate_summary(self, results: Dict[str, Any]) -> str:
        """Generate summary from results"""
        successful = sum(1 for r in results.values() if "error" not in r)
        total = len(results)
        return f"Completed {successful}/{total} subtasks successfully"

    async def start(self):
        """Start coordinator"""
        self._running = True
        logger.info("Agent coordinator started")

    async def stop(self):
        """Stop coordinator"""
        self._running = False
        logger.info("Agent coordinator stopped")


# Global coordinator instance
_coordinator: Optional[AgentCoordinator] = None


def get_coordinator() -> AgentCoordinator:
    """Get global coordinator instance"""
    global _coordinator
    if _coordinator is None:
        _coordinator = AgentCoordinator()
    return _coordinator
