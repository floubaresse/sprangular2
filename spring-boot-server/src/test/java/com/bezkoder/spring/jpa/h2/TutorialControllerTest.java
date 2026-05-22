package com.bezkoder.spring.jpa.h2;

import com.bezkoder.spring.jpa.h2.repository.TutorialRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@SpringBootTest
@AutoConfigureMockMvc
class TutorialControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private TutorialRepository repository;

    @BeforeEach
    void setUp() {
        repository.deleteAll();
    }

    @Test
    void createTutorial_returns201WithTitle() throws Exception {
        mockMvc.perform(post("/api/tutorials")
                .contentType(MediaType.APPLICATION_JSON)
                .content("{\"title\":\"Spring Boot Basics\",\"description\":\"Intro\",\"published\":false}"))
            .andExpect(status().isCreated())
            .andExpect(jsonPath("$.title").value("Spring Boot Basics"));
    }

    @Test
    void listTutorials_returnsCreatedItem() throws Exception {
        mockMvc.perform(post("/api/tutorials")
                .contentType(MediaType.APPLICATION_JSON)
                .content("{\"title\":\"Angular Guide\",\"description\":\"Frontend\",\"published\":true}"));

        mockMvc.perform(get("/api/tutorials"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$[0].title").value("Angular Guide"));
    }

    @Test
    void deleteAllTutorials_returnsEmptyList() throws Exception {
        mockMvc.perform(post("/api/tutorials")
                .contentType(MediaType.APPLICATION_JSON)
                .content("{\"title\":\"To Delete\",\"description\":\"Temp\",\"published\":false}"));

        mockMvc.perform(delete("/api/tutorials"))
            .andExpect(status().isNoContent());

        mockMvc.perform(get("/api/tutorials"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$").isEmpty());
    }
}
