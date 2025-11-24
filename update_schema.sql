ALTER TABLE Appointments
ADD payment_status VARCHAR(20) DEFAULT 'pending', -- pending, paid, partial
    payment_method VARCHAR(20), -- cash, nequi, daviplata, transfer
    payment_proof VARCHAR(255), -- path to image or 'cash'
    payment_amount DECIMAL(10, 2) DEFAULT 0;
