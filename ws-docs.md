### WebSocket Documentation


This documents identifies `OUT` as the server message and `IN` as the client message. 


#### Authentication methods


##### 1. Query Params (Recommended)

Set a query params on connect with auth=token


example: /list/?auth=AOSIJDAOSIHFASFUH


##### 2. Cookie

Set a cookie userToken with the token authenticated.

userToken=OIASJNDOIASFIOAF


## /ws/quiz/list

#### IN and OUT Messages

---

**OUT ON CONNECT: Competition List**  
- **Description:** Sent by the server when a client connects, providing a list of available competitions.
- **Message Format:**
  ```json
  {
    "type": "competition_list",
    "data": [
      {
        "id": 2,
        "questions": [
          {"pk": 1, "number": 1},
          {"pk": 2, "number": 2},
          {"pk": 3, "number": 3},
          {"pk": 4, "number": 4},
          {"pk": 5, "number": 5}
        ],
        "sponsors": [],
        "participantsCount": 1,
        "title": "test 2",
        "details": "123213",
        "createdAt": "2024-09-25T08:42:29.207670Z",
        "startAt": "2024-09-26T07:19:01Z",
        "prizeAmount": 100000.0,
        "chainId": 10,
        "tokenDecimals": 6,
        "token": "USDC",
        "tokenAddress": "0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9",
        "discordUrl": null,
        "twitterUrl": null,
        "emailUrl": "alimaktabi55@yahoo.com",
        "telegramUrl": null,
        "tokenImage": null,
        "image": null,
        "shuffleAnswers": true,
        "splitPrize": true,
        "txHash": "0x00",
        "isActive": true,
        "hintCount": 1,
        "userProfile": 1
      },
      {
        "id": 1,
        "questions": [],
        "sponsors": [],
        "participantsCount": 1,
        "title": "test 3",
        "details": "12313",
        "createdAt": "2024-09-25T08:39:53.910329Z",
        "startAt": "2024-09-26T07:02:56Z",
        "prizeAmount": 100000.0,
        "chainId": 10,
        "tokenDecimals": 6,
        "token": "USDC",
        "tokenAddress": "0x4F604735c1cF31399C6E711D5962b2B3E0225AD3",
        "discordUrl": null,
        "twitterUrl": null,
        "emailUrl": "alimaktabi55@yahoo.com",
        "telegramUrl": null,
        "tokenImage": null,
        "image": null,
        "shuffleAnswers": false,
        "splitPrize": true,
        "txHash": null,
        "isActive": true,
        "hintCount": 1,
        "userProfile": 1
      }
    ]
  }
  ```

---

**OUT ON CONNECT (If Authenticated): User Enrollments**  
- **Description:** Sent by the server when a client connects, providing a list of competitions the user is enrolled in along with their status and winnings.
- **Message Format:**
  ```json
  {
    "type": "user_enrolls",
    "data": [
      {
        "id": 1,
        "competition": Competition,
        "isWinner": true,
        "amountWon": 100000.0,
        "hintCount": 1,
        "txHash": "",
        "userProfile": 1
      },
      {
        "id": 2,
        "competition": Competition,
        "isWinner": false,
        "amountWon": 0.0,
        "hintCount": 0,
        "txHash": "",
        "userProfile": 1
      }
    ]
  }
  ```

---

**OUT ON UPDATE OR CREATE COMPETITION**  
- **Description:** Sent by the server when a new competition is created or an existing competition is updated.
- **Message Format:**
  ```json
  {
    "type": "update_competition",
    "data": {
      "id": 2,
      "questions": [
        {"pk": 1, "number": 1},
        {"pk": 2, "number": 2},
        {"pk": 3, "number": 3},
        {"pk": 4, "number": 4},
        {"pk": 5, "number": 5}
      ],
      "sponsors": [],
      "participantsCount": 1,
      "title": "test 2",
      "details": "123213",
      "createdAt": "2024-09-25T08:42:29.207670Z",
      "startAt": "2024-09-26T07:19:01Z",
      "prizeAmount": 100000.0,
      "chainId": 10,
      "tokenDecimals": 6,
      "token": "USDC",
      "tokenAddress": "0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9",
      "discordUrl": null,
      "twitterUrl": null,
      "emailUrl": "alimaktabi55@yahoo.com",
      "telegramUrl": null,
      "tokenImage": null,
      "image": null,
      "shuffleAnswers": true,
      "splitPrize": true,
      "txHash": "0x00",
      "isActive": true,
      "hintCount": 1,
      "userProfile": 1
    }
  }
  ```

---

**OUT ON INCREASE QUIZ MEMBERS**  
- **Description:** Sent by the server when the number of quiz members (participants) increases.
- **Message Format:**
  ```json
  {
    "type": "increase_enrollment",
    "data": 3
  }
  ```


##  /ws/quiz/:id

#### IN and OUT Messages



---

**IN: PING Command**  
- **Description:** Sent by the client to check the connection status.
- **Message Format:**
  ```json
  {"command": "PING"}
  ```

- **OUT: PONG Response**
  - **Description:** Sent by the server as a response to the `PING` command, confirming the connection is alive.
  - **Message Format:**
    ```json
    "PONG"
    ```

---

**OUT ON CONNECT: Answers History**
- **Description:** Sent by the server when a client connects, providing the history of the user's answers.
- **Message Format:**
  ```json
  {
    "type": "answers_history",
    "data": [] # number[]
  }
  ```

---

**OUT ON CONNECT: Quiz Stats**
- **Description:** Sent by the server on client connection, providing the current quiz statistics.
- **Message Format:**
  ```json
  {
    "type": "quiz_stats",
    "data": {
      "usersParticipating": 1,
      "prizeToWin": 100000.0,
      "totalParticipantsCount": 1,
      "questionsCount": 5,
      "hintCount": 1,
      "previousRoundLosses": 0
    }
  }
  ```

---

**OUT ON CONNECT: Idle Message**
- **Description:** Sent by the server on client connection if the quiz has not started, notifying the user to wait.
- **Message Format:**
  ```json
  {
    "type": "idle",
    "message": "wait for quiz to start"
  }
  ```

---

**IN: GET_STATS Command**  
- **Description:** Sent by the client to request current quiz statistics.
- **Message Format:**
  ```json
  {"command": "GET_STATS"}
  ```

- **OUT: Quiz Stats Response**
  - **Description:** Sent by the server in response to `GET_STATS`, providing the requested quiz statistics.
  - **Message Format:**
    ```json
    {
      "type": "quiz_stats",
      "data": {
        "usersParticipating": 1,
        "prizeToWin": 100000.0,
        "totalParticipantsCount": 1,
        "questionsCount": 5,
        "hintCount": 1,
        "previousRoundLosses": 0
      }
    }
    ```

---

**OUT ON CRONJOB TRIGGER: New Question**  
- **Description:** Sent by the server when a new question is triggered during the quiz.
- **Message Format:**
  ```json
  {
    "question": {
      "id": 1,
      "choices": [
        {"id": 4, "isCorrect": null, "text": "4", "question": 1},
        {"id": 2, "isCorrect": null, "text": "2", "question": 1},
        {"id": 3, "isCorrect": null, "text": "3", "question": 1},
        {"id": 1, "isCorrect": null, "text": "1", "question": 1}
      ],
      "remainParticipantsCount": 0,
      "totalParticipantsCount": 1,
      "amountWonPerUser": null,
      "isEligible": true,
      "number": 1,
      "text": "test",
      "competition": 2
    },
    "type": "new_question"
  }
  ```

---

**IN: ANSWER Command**  
- **Description:** Sent by the client when answering a question during the quiz.
- **Message Format:**
  ```json
  {
    "command": "ANSWER",
    "args": {
      "questionId": 1,
      "selectedChoiceId": 1
    }
  }
  ```

- **OUT: Add Answer Response**
  - **Description:** Sent by the server after processing the user's answer, indicating whether the answer was correct and providing the updated competition details.
  - **Message Format:**
    ```json
    {
      "type": "add_answer",
      "data": {
        "isCorrect": true,
        "answer": {
          "id": 2,
          "userCompetition": {
            "id": 2,
            "competition": Competition,
            "isWinner": false,
            "amountWon": 0.0
          },
          "selectedChoice": {
            "id": 1,
            "isCorrect": true,
            "text": "1",
            "question": 1
          },
          "question": 1
        },
        "questionNumber": 1,
        "correctChoice": 1,
        "isEligible": true,
        "questionId": 1
      }
    }
    ```

---

**IN: GET_HINT Command**  
- **Description:** Sent by the client to request a hint for a particular question.
- **Message Format:**
  ```json
  {
    "command": "GET_HINT",
    "args": {
      "question_id": 4
    }
  }
  ```

- **OUT: Hint Question Response**
  - **Description:** Sent by the server in response to the `GET_HINT` command, providing choice ids to remove as invalid choice for the requested question.
  - **Message Format:**
    ```json
    {
      "type": "hint_question",
      "data": [14, 15],
      "questionId": 4
    }
    ```

---

**OUT ON CRONJOB TRIGGER: Quiz Finish**  
- **Description:** Sent by the server when the quiz finishes, providing a list of winners.
- **Message Format:**
  ```json
  {
    "winnersList": [], # string[]
    "type": "quiz_finish"
  }
  ```