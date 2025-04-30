# Coding Challenge

Create a game state handler for league of legends that can process multiple types of
events and produce kill streaks and sprees. 


## Non-technical conditions & limitations

1. All incoming events should be saved into the database (of your choice)
   
    *Note:* you will only need `kill` events to produce kill streaks/sprees, but you must save all the events into the database.
2. More event types can be added in the future, so keep your implementation expandable.
3. This module is a part of the larger system that maintains a complete state of the game with states of each player, items, dragons etc. Of course, you don't have to implement the whole system.


## Technical conditions & limitations

1. You are free to create any files and use external libraries if needed.
2. Virtually, events flow in via an asynchronous queue (i.e. RabbitMQ).
   It is not necessary to implement this exact flow in this tech challenge,
   but can help make certain system design decisions.
3. Prioritize fast consumption of the events so that the async queue is not clogged up.
4. Kill streaks and sprees are not required to be produced at the time of them happening. Feel free to produce them at any time during or after the match


## Descriptions of possible events

Events are represented as a json containing the event type, 
and a payload with the specific information about this event.

```json
{
    "type": "MATCH_EVENT",
    "payload": {
        "field1": "value",
        "field2": "value2"
    },
    "timestamp": "2024-04-03 13:55:41"
}
```

Events have different meanings based on their type, and their payloads can have different
fields depending on the information they need to convey. However, all events of one type
are always guaranteed to have the same set of fields.

Below is a description of each of the event types, and their expected effect:

* `MATCH_START`: Initializes a new game state. Contains all the initial information about
  the game, the teams and their players. This event is always guaranteed to arrive first.
* `MINION_KILL`: A player killed a minion. The player is granted some gold and their
  minion count is updated.
* `PLAYER_KILL`: One player killed another, optionally assisted by other members of the
  team. The killer is granted some gold, and each of the assistants receive a reduced
  amount. Kills, deaths and assists stats should be updated for all the players involved.
* `DRAGON_KILL`: One player killed a dragon. The team's dragon kill count should be
  updated, and the player is granted some gold.
* `TURRET_DESTROY`: A team destroyed an enemy turret. The team's tower kill count should
  be updated, and each of its players receives some gold. Additionally, the player who
  took the tower receives `playerGoldGranted` gold. Keep in mind that sometimes towers
  are destroyed by minions, so no individual player receives `playerGold`, although team
  gold is still granted.
* `MATCH_END`: The match ended, and a winner is declared. There are never any events
  after this one.

Watch out for events that are unparsable or have incomplete information.
Some of these events will have enough information to account them into the streaks/sprees,
others should be skipped altogether.

## Descriptions of streaks and sprees:

### Double/Triple/Quadra/Penta kills

A killing streak is defined as a multitude of kills done in a time-window of 10 seconds,
counted from the last event in the streak.

Double kill – 2 consecutive kills
Triple kill – 3 consecutive kills
Quadra kill – 4 consecutive kills
Penta kill – 5 consecutive kills

*Example 1*: a kill at time `T` is followed by a kill at `T+5s` is considered a **double kill**.

*Example 2*: kills at `T`, `T+8s` and `T+15s` are considered a **triple kill**.

*Example 3*: kills at `T`, `T+8` and `T+20` are considered a double kill + single kill (since more than 10s have passed from second to third kill)

#### Conditions & limitations:
- Time window size should be a config-value
- Double, triple and quadra kills is required, penta kills is optional
- Bonus points: if a triple kill at `T`, `T+5` and `T+10` **doesn’t** produce two double kills `(T, T+5)` and `(T+5, T+10)`


### Killing spree/Rampage/Unstoppable/Dominating/Godlike
A spree is defined by a multitude of kills by a player before a death

3 kills – Killing spree
4 kills – Rampage
5 kills – Unstoppable
6 kills – Dominating
7 kills – Godlike

*Example*: Allied Player 1 (AP1) kills Enemy Player 1 (EP1),  EP2 and EP3, then dies. That is considered a **killing spree**.

#### Conditions & limitations:
- Bonus points: if a higher-rank spree doesn’t produce any lower-rank sprees.
  - Example: if there’s a rampage for AP1, there are no killing sprees produced with the same kills.
- Killing spree, Rampage and Unstoppable are required, dominating and godlike are optional

### First blood
First blood is defined as a first **player-player** kill in the game. Player kills by minions, turrets and dragons don't count as a first blood.


# Testing
Write unit tests that verify the behavior of your implementation. `Pytest` is encouraged,
but you are allowed to use other frameworks of your choice.

We are not looking for full test coverage in this part. It is enough with creating tests for these events only:

* `Double Kill`
* `Triple Kill`
* `Quadra Kill`
* `Penta Kill`

To keep the challenge brief, we will only review tests for these four events, and any
further coverage will not be considered in the code review.

