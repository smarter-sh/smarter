-- MySQL dump 10.13  Distrib 9.6.0, for macos26.2 (arm64)
--
-- Database: smarter_test_db
-- ------------------------------------------------------
-- Server version	8.4.9

--
-- Grant the smarter application user superuser privileges
--

GRANT ALL PRIVILEGES ON *.* TO 'smarter'@'%' WITH GRANT OPTION;

--
-- Create read-only test users for smarter_test_db
--

CREATE USER IF NOT EXISTS 'smarter_test_proxy_user'@'%' IDENTIFIED BY 'smarter_test_proxy_user';
GRANT SELECT ON smarter_test_db.* TO 'smarter_test_proxy_user'@'%';

CREATE USER IF NOT EXISTS 'smarter_test_user'@'%' IDENTIFIED BY 'smarter_test_user';
GRANT SELECT ON smarter_test_db.* TO 'smarter_test_user'@'%';

FLUSH PRIVILEGES;

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;
SET @MYSQLDUMP_TEMP_LOG_BIN = @@SESSION.SQL_LOG_BIN;
SET @@SESSION.SQL_LOG_BIN= 0;

--
-- Current Database: `smarter_test_db`
--

/*!40000 DROP DATABASE IF EXISTS `smarter_test_db`*/;

CREATE DATABASE /*!32312 IF NOT EXISTS*/ `smarter_test_db` /*!40100 DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci */ /*!80016 DEFAULT ENCRYPTION='N' */;

USE `smarter_test_db`;

--
-- Table structure for table `courses`
--

DROP TABLE IF EXISTS `courses`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `courses` (
  `course_id` int NOT NULL AUTO_INCREMENT,
  `course_code` varchar(10) NOT NULL,
  `course_name` varchar(100) NOT NULL,
  `description` varchar(255) NOT NULL,
  `cost` decimal(8,2) NOT NULL,
  `prerequisite_id` int DEFAULT NULL,
  PRIMARY KEY (`course_id`),
  UNIQUE KEY `course_code` (`course_code`),
  KEY `prerequisite_id` (`prerequisite_id`),
  CONSTRAINT `courses_ibfk_1` FOREIGN KEY (`prerequisite_id`) REFERENCES `courses` (`course_id`)
) ENGINE=InnoDB AUTO_INCREMENT=49 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `courses`
--

LOCK TABLES `courses` WRITE;
/*!40000 ALTER TABLE `courses` DISABLE KEYS */;
INSERT INTO `courses` VALUES (1,'CS101','Introduction to Computer Science','Fundamental concepts of computer science and programming.',500.00,NULL),(2,'CS102','Programming Fundamentals','Introduction to programming using Python.',500.00,1),(3,'CS103','Discrete Mathematics','Mathematical foundations for computer science.',450.00,1),(4,'CS104','Data Structures','Study of data organization and manipulation.',550.00,2),(5,'CS105','Computer Organization','Introduction to computer hardware and architecture.',500.00,1),(6,'CS106','Object-Oriented Programming','Principles of object-oriented design and programming.',550.00,2),(7,'CS107','Algorithms','Design and analysis of algorithms.',600.00,4),(8,'CS108','Operating Systems','Concepts of modern operating systems.',600.00,5),(9,'CS109','Database Systems','Introduction to relational databases and SQL.',550.00,2),(10,'CS110','Software Engineering','Software development lifecycle and methodologies.',600.00,6),(11,'CS201','Web Development','Building dynamic web applications.',500.00,6),(12,'CS202','Computer Networks','Principles of data communication and networking.',600.00,5),(13,'CS203','Theory of Computation','Automata, computability, and complexity.',650.00,3),(14,'CS204','Programming Languages','Design and implementation of programming languages.',600.00,6),(15,'CS205','Mobile App Development','Developing applications for mobile devices.',600.00,6),(16,'CS206','Human-Computer Interaction','Designing user-friendly interfaces.',500.00,6),(17,'CS207','Cloud Computing Fundamentals','Introduction to cloud platforms and services.',650.00,9),(18,'CS208','Distributed Systems','Principles of distributed computing.',700.00,8),(19,'CS209','Cybersecurity Basics','Fundamentals of computer and network security.',600.00,5),(20,'CS210','Artificial Intelligence','Introduction to AI concepts and techniques.',700.00,7),(21,'CS301','Machine Learning','Supervised and unsupervised learning algorithms.',750.00,20),(22,'CS302','Deep Learning','Neural networks and deep learning architectures.',800.00,21),(23,'CS303','Natural Language Processing','Computational techniques for language understanding.',800.00,21),(24,'CS304','Cloud Architecture','Designing scalable cloud solutions.',750.00,17),(25,'CS305','Big Data Analytics','Techniques for processing large datasets.',800.00,17),(26,'CS306','DevOps Practices','Continuous integration and deployment.',700.00,17),(27,'CS307','Cloud Security','Securing cloud-based applications.',750.00,17),(28,'CS308','AI Ethics','Ethical considerations in artificial intelligence.',600.00,20),(29,'CS309','Reinforcement Learning','Learning through interaction with environments.',850.00,21),(30,'CS310','Computer Vision','Image processing and computer vision techniques.',800.00,21),(31,'CS311','Parallel Computing','Techniques for parallel and high-performance computing.',750.00,8),(32,'CS312','Quantum Computing','Introduction to quantum algorithms and hardware.',900.00,13),(33,'CS313','Cloud Native Development','Building applications for the cloud.',750.00,17),(34,'CS314','Edge Computing','Computing at the edge of the network.',700.00,17),(35,'CS315','Data Mining','Extracting knowledge from large datasets.',750.00,21),(36,'CS316','AI for Robotics','Applying AI techniques to robotics.',850.00,21),(37,'CS317','Cloud Automation','Automating cloud infrastructure and services.',700.00,17),(38,'CS318','Serverless Computing','Building applications without managing servers.',700.00,17),(39,'CS319','AI in Healthcare','Applications of AI in healthcare.',800.00,21),(40,'CS320','Cloud Migration','Strategies for migrating to the cloud.',700.00,17),(41,'CS401','Advanced Algorithms','Advanced topics in algorithm design.',850.00,7),(42,'CS402','Advanced Database Systems','NoSQL, NewSQL, and distributed databases.',850.00,9),(43,'CS403','Advanced Operating Systems','Topics in modern OS design.',850.00,8),(44,'CS404','Advanced Computer Networks','Network protocols and architectures.',850.00,12),(45,'CS405','AI Capstone Project','Team-based AI project.',1000.00,21),(46,'CS406','Cloud Capstone Project','Team-based cloud computing project.',1000.00,17),(47,'CS407','Research Methods in CS','Research techniques and scientific writing.',600.00,3),(48,'CS408','Professional Practice','Ethics and professionalism in computing.',600.00,10);
/*!40000 ALTER TABLE `courses` ENABLE KEYS */;
UNLOCK TABLES;


--
-- Dumping routines for database 'smarter_test_db'
--
--
-- WARNING: can't read the INFORMATION_SCHEMA.libraries table. It's most probably an old server 8.4.9.
--
SET @@SESSION.SQL_LOG_BIN = @MYSQLDUMP_TEMP_LOG_BIN;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-08-05 12:30:31
