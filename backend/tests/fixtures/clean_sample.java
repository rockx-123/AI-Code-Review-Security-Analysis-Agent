// Deliberately clean, reasonably well-written sample code — used to confirm the agents don't
// flag ordinary, non-vulnerable code (a basic false-positive check for Milestone 2, Task 4).
import java.sql.*;

public class CleanSample {

    public User getUserById(Connection conn, int userId) throws Exception {
        PreparedStatement stmt = conn.prepareStatement("SELECT * FROM users WHERE id = ?");
        stmt.setInt(1, userId);
        ResultSet rs = stmt.executeQuery();
        return null;
    }

    public int add(int a, int b) {
        return a + b;
    }

    public double calculateTotal(java.util.List<Item> items) {
        double total = 0;
        for (Item item : items) {
            total += item.getPrice();
        }
        return total;
    }
}
