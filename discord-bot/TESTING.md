# Neural Cord Testing Guide

This document outlines procedures for testing Neural Cord during the beta phase.

## Test Environment Setup

1. Create a dedicated Discord server for testing
2. Set up the bot on this server following the installation instructions in the README
3. Configure at least two different characters for testing

## Basic Functionality Testing

### Authentication
- [ ] Test `/login` command with valid Character.AI credentials
- [ ] Test `/verify` command with valid verification link
- [ ] Verify bot shows as authenticated in `/info` command

### Character Management
- [ ] Test `/setcharacter` with valid character ID
- [ ] Test `/listcharacters` shows all configured characters
- [ ] Test `/resetchat` successfully resets conversation
- [ ] Test `/deletechat` removes character from list

### Conversations
- [ ] Test `/chat` command with simple greeting
- [ ] Test `/chat` with complex questions
- [ ] Test `/talk` with specific character ID
- [ ] Verify character responses match expected personality

## Social Mode Testing

### Configuration
- [ ] Test `/socialmode true` enables Social Mode
- [ ] Test `/addchannel` adds current channel to Social Mode
- [ ] Test `/removechannel` removes channel from Social Mode
- [ ] Test `/setcooldown` changes response frequency

### Conversation Detection
- [ ] Test direct mentions of character (e.g., "Hey Monika")
- [ ] Test indirect references to character
- [ ] Test conversations between multiple users
- [ ] Test conversation with character-specific topics

### Edge Cases
- [ ] Test with very long messages
- [ ] Test with messages containing code blocks
- [ ] Test with messages containing URLs
- [ ] Test with messages containing emoji and special characters
- [ ] Test with messages directed at other users

### Inappropriate Content Filtering
- [ ] Test mildly inappropriate content
- [ ] Test message with profanity
- [ ] Test requests for harmful information
- [ ] Verify filtering correctly identifies inappropriate content

## Performance Testing

- [ ] Test response time for direct commands
- [ ] Test response time in Social Mode
- [ ] Test with multiple simultaneous users
- [ ] Test rate limiting functionality
- [ ] Monitor CPU and memory usage during operation

## Reporting Issues

When reporting issues, please include:

1. Steps to reproduce the issue
2. What you expected to happen
3. What actually happened
4. Bot logs (from bot.log or filter_ai.log)
5. Screenshots if applicable

Please report issues through:
- GitHub Issues: [GitHub Repository](https://github.com/IvailoStoianov/NeuralCord)

## Feedback Format

```
Feature: [Feature you're providing feedback on]
Rating (1-5): [Your rating]
What worked well: [Positive feedback]
What needs improvement: [Constructive feedback]
Suggestions: [Your ideas for improvement]
```

Thank you for helping test Neural Cord! 