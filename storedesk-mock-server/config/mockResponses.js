module.exports = {
  happy_path: {
    stock: { isSuccess: true, message: "Stock monitoring updated successfully" },
    price: { isSuccess: true, message: "Price monitoring updated successfully" }
  },
  partial_failure: {
    stock: { isSuccess: true, message: "Stock monitoring updated successfully" },
    price: { isSuccess: false, message: "Failed to update price monitoring" }
  },
  full_failure: {
    stock: { isSuccess: false, message: "Failed to update stock monitoring" },
    price: { isSuccess: false, message: "Failed to update price monitoring" }
  },
  slow_response: {
    stock: { isSuccess: true, message: "Stock monitoring updated successfully" },
    price: { isSuccess: true, message: "Price monitoring updated successfully" }
  },
  auth_failure: {
    stock: { isSuccess: false, message: "Unauthorized" },
    price: { isSuccess: false, message: "Unauthorized" }
  }
};
