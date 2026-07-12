CREATE TABLE leave_applications (
    id             SERIAL PRIMARY KEY,
    emp_id         INTEGER NOT NULL REFERENCES employees(emp_id),
    leave_type     VARCHAR NOT NULL,
    start_date     DATE NOT NULL,
    end_date       DATE NOT NULL,
    working_days   INTEGER NOT NULL,
    reason         VARCHAR NOT NULL,
    pending_to     INTEGER REFERENCES employees(emp_id),
    status         VARCHAR NOT NULL DEFAULT 'pending',
    applied_on     TIMESTAMP NOT NULL DEFAULT NOW(),
    actioned_on    TIMESTAMP,
    decline_reason VARCHAR
);
