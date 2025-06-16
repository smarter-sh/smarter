-- read-only user
-- ----------------------------------------------------------
-- host:  sql.lawrencemcdaniel.com
-- port:  3306
-- db:	  smarter_test_db
-- user:  smarter_test_user
-- pwd:	  <--- password -->
-- ----------------------------------------------------------

-- Create the test database
DROP DATABASE IF EXISTS smarter_test_db;
CREATE DATABASE smarter_test_db;
USE smarter_test_db;

-- Create the test user and grant privileges
CREATE USER IF NOT EXISTS 'test_user'@'localhost' IDENTIFIED BY 'test_user';
GRANT ALL PRIVILEGES ON smarter_test_db.* TO 'test_user'@'localhost';
FLUSH PRIVILEGES;

-- Create the 'courses' table
CREATE TABLE courses (
    course_id INT AUTO_INCREMENT PRIMARY KEY,
    course_code VARCHAR(10) NOT NULL UNIQUE,
    course_name VARCHAR(100) NOT NULL,
    description VARCHAR(255) NOT NULL,
    cost DECIMAL(8,2) NOT NULL,
    prerequisite_id INT DEFAULT NULL,
    FOREIGN KEY (prerequisite_id) REFERENCES courses(course_id)
);

-- Insert 50 fictional but realistic courses
INSERT INTO courses (course_code, course_name, description, cost, prerequisite_id) VALUES
('CS101', 'Introduction to Computer Science', 'Fundamental concepts of computer science and programming.', 500.00, NULL),
('CS102', 'Programming Fundamentals', 'Introduction to programming using Python.', 500.00, 1),
('CS103', 'Discrete Mathematics', 'Mathematical foundations for computer science.', 450.00, 1),
('CS104', 'Data Structures', 'Study of data organization and manipulation.', 550.00, 2),
('CS105', 'Computer Organization', 'Introduction to computer hardware and architecture.', 500.00, 1),
('CS106', 'Object-Oriented Programming', 'Principles of object-oriented design and programming.', 550.00, 2),
('CS107', 'Algorithms', 'Design and analysis of algorithms.', 600.00, 4),
('CS108', 'Operating Systems', 'Concepts of modern operating systems.', 600.00, 5),
('CS109', 'Database Systems', 'Introduction to relational databases and SQL.', 550.00, 2),
('CS110', 'Software Engineering', 'Software development lifecycle and methodologies.', 600.00, 6),
('CS201', 'Web Development', 'Building dynamic web applications.', 500.00, 6),
('CS202', 'Computer Networks', 'Principles of data communication and networking.', 600.00, 5),
('CS203', 'Theory of Computation', 'Automata, computability, and complexity.', 650.00, 3),
('CS204', 'Programming Languages', 'Design and implementation of programming languages.', 600.00, 6),
('CS205', 'Mobile App Development', 'Developing applications for mobile devices.', 600.00, 6),
('CS206', 'Human-Computer Interaction', 'Designing user-friendly interfaces.', 500.00, 6),
('CS207', 'Cloud Computing Fundamentals', 'Introduction to cloud platforms and services.', 650.00, 9),
('CS208', 'Distributed Systems', 'Principles of distributed computing.', 700.00, 8),
('CS209', 'Cybersecurity Basics', 'Fundamentals of computer and network security.', 600.00, 5),
('CS210', 'Artificial Intelligence', 'Introduction to AI concepts and techniques.', 700.00, 7),
('CS301', 'Machine Learning', 'Supervised and unsupervised learning algorithms.', 750.00, 20),
('CS302', 'Deep Learning', 'Neural networks and deep learning architectures.', 800.00, 21),
('CS303', 'Natural Language Processing', 'Computational techniques for language understanding.', 800.00, 21),
('CS304', 'Cloud Architecture', 'Designing scalable cloud solutions.', 750.00, 17),
('CS305', 'Big Data Analytics', 'Techniques for processing large datasets.', 800.00, 17),
('CS306', 'DevOps Practices', 'Continuous integration and deployment.', 700.00, 17),
('CS307', 'Cloud Security', 'Securing cloud-based applications.', 750.00, 17),
('CS308', 'AI Ethics', 'Ethical considerations in artificial intelligence.', 600.00, 20),
('CS309', 'Reinforcement Learning', 'Learning through interaction with environments.', 850.00, 21),
('CS310', 'Computer Vision', 'Image processing and computer vision techniques.', 800.00, 21),
('CS311', 'Parallel Computing', 'Techniques for parallel and high-performance computing.', 750.00, 8),
('CS312', 'Quantum Computing', 'Introduction to quantum algorithms and hardware.', 900.00, 13),
('CS313', 'Cloud Native Development', 'Building applications for the cloud.', 750.00, 17),
('CS314', 'Edge Computing', 'Computing at the edge of the network.', 700.00, 17),
('CS315', 'Data Mining', 'Extracting knowledge from large datasets.', 750.00, 21),
('CS316', 'AI for Robotics', 'Applying AI techniques to robotics.', 850.00, 21),
('CS317', 'Cloud Automation', 'Automating cloud infrastructure and services.', 700.00, 17),
('CS318', 'Serverless Computing', 'Building applications without managing servers.', 700.00, 17),
('CS319', 'AI in Healthcare', 'Applications of AI in healthcare.', 800.00, 21),
('CS320', 'Cloud Migration', 'Strategies for migrating to the cloud.', 700.00, 17),
('CS401', 'Advanced Algorithms', 'Advanced topics in algorithm design.', 850.00, 7),
('CS402', 'Advanced Database Systems', 'NoSQL, NewSQL, and distributed databases.', 850.00, 9),
('CS403', 'Advanced Operating Systems', 'Topics in modern OS design.', 850.00, 8),
('CS404', 'Advanced Computer Networks', 'Network protocols and architectures.', 850.00, 12),
('CS405', 'AI Capstone Project', 'Team-based AI project.', 1000.00, 21),
('CS406', 'Cloud Capstone Project', 'Team-based cloud computing project.', 1000.00, 17),
('CS407', 'Research Methods in CS', 'Research techniques and scientific writing.', 600.00, 3),
('CS408', 'Professional Practice', 'Ethics and professionalism in computing.', 600.00, 10);
