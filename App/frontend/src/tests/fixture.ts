import type { Product } from "../domain/product";
export const product: Product = {
  id: 1,
  name: "Everyday Cotton Tee",
  description: "日常纯棉 T 恤",
  image: "/static/products/tee-black-s.svg",
  dimensions: [
    {
      id: 1,
      name: "Color",
      values: [
        { id: 1, value: "Black" },
        { id: 2, value: "White" },
        { id: 3, value: "Blue" },
      ],
    },
    {
      id: 2,
      name: "Size",
      values: [
        { id: 4, value: "S" },
        { id: 5, value: "M" },
        { id: 6, value: "L" },
      ],
    },
  ],
  skus: [
    {
      id: 1,
      price: 129,
      available_quantity: 10,
      image: "/static/products/tee-black-s.svg",
      is_available: true,
      option_value_ids: [1, 4],
    },
    {
      id: 2,
      price: 139,
      available_quantity: 0,
      image: "/static/products/tee-black-m.svg",
      is_available: true,
      option_value_ids: [1, 5],
    },
    {
      id: 3,
      price: 149,
      available_quantity: 3,
      image: "/static/products/tee-white-s.svg",
      is_available: true,
      option_value_ids: [2, 4],
    },
    {
      id: 4,
      price: 159,
      available_quantity: 5,
      image: "/static/products/tee-blue-s.svg",
      is_available: false,
      option_value_ids: [3, 4],
    },
  ],
};
